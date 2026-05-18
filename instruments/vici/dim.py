import serial
from enum import Enum, auto
from core.logging import flow_logger as logger, log_call
from core.tracing import append_trace

class DIMState(Enum):
    LOAD = auto()
    INJECT = auto()
    UNKNOWN = auto() #initial state or error state

class DIM:
    """
    Minimal controller for a 2-position Vici Cheminert valve (A/B) via RS-232.
    """

    def __init__(self, port="COM5", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

        # DIM is given an identifier for the tray 
        self.module_id = "dim"

        # --- Z limits ---
        self.z_limits = {
            "safe": 127.0,
            "max_safe": 127.0,
            "working_min": 79    
        }

        # --- State tracking ---
        self.state = DIMState.UNKNOWN
        

    def connect(self):
        """Open the serial port."""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=self.timeout
        )

        if self.ser.is_open:
            print(f"Connected to DIM on {self.port}")
        else:
            raise Exception("Could not open serial port")

    def _send(self, cmd: str) -> str:
        """
        Internal helper to send ASCII commands with \r and return decoded response.
        """
        if not self.ser or not self.ser.is_open:
            raise Exception("Serial port not open")

        self.ser.write((cmd + "\r").encode("ascii"))
        resp = self.ser.readline().decode(errors="ignore")
        return resp.strip()

    def read_pos(self) -> str:
        """
        Reads current position. 'CP' returns a string whose second-last
        character is usually the position letter ('A' or 'B').
        """
        resp = self._send("CP")
        if len(resp) < 2:
            return "?"
        return resp[-1]  # sometimes last char is the position

    @log_call
    def go_to_pos(self, pos: str, dry_run=False, trace=None):
        """
        Moves valve to 'A' or 'B'.
        A = CW   (clockwise)
        B = CC   (counter-clockwise)
        """
        pos = pos.upper()

        if dry_run:
            if pos == "A":
                self.state = DIMState.INJECT
            elif pos == "B":
                self.state = DIMState.LOAD
            else:
                raise ValueError("Position must be 'A' or 'B'")

            append_trace(
                trace,
                step="dim",
                action="go_to_pos",
                module="dim",
                notes=pos,
            )
            print(f"[DIM] Dry-run valve to {pos} -> state = {self.state}")
            return

        current = self.read_pos()
    
        # --- Always sync internal state with hardware ---
        if current == "A":
            self.state = DIMState.INJECT
        elif current == "B":
            self.state = DIMState.LOAD
        else:
            self.state = DIMState.UNKNOWN
    
        if current == pos:
            print(f"[DIM] Valve already at {pos} -> state = {self.state}")
            return
    
        if pos == "A":
            self._send("CW")
            self.state = DIMState.INJECT
        elif pos == "B":
            self._send("CC")
            self.state = DIMState.LOAD
        else:
            raise ValueError("Position must be 'A' or 'B'")
    
        print(f"[DIM] Valve moved to {pos} -> state = {self.state}")

    @log_call
    def toggle(self):
        """Switches A→B or B→A."""
        p = self.read_pos()
        if p == "A":
            self.go_to_pos("B")
        elif p == "B":
            self.go_to_pos("A")
        else:
            print(f"Unknown position '{p}' — cannot toggle.")

    def load(self, dry_run=False, trace=None):
        """ Connects injection assay to sample loop """
        append_trace(trace, step="dim", action="load", module="dim")
        self.go_to_pos("B", dry_run=dry_run, trace=trace)

    def inject(self, dry_run=False, trace=None):
        """ Connects injection assay to waste (gas/solvent from Runze toward sample loop now) """
        append_trace(trace, step="dim", action="inject", module="dim")
        self.go_to_pos("A", dry_run=dry_run, trace=trace)

    def assert_load(self, dry_run=False, trace=None):
        """
        Ensure the DIM is in LOAD (B) position.
        Sync internal state with hardware before asserting.
        """
        if dry_run:
            append_trace(trace, step="dim", action="assert_load", module="dim")
            if self.state != DIMState.LOAD:
                raise RuntimeError(
                    f"DIM must be in LOAD to accept liquid. "
                    f"Internal state: {self.state}"
                )
            return

        pos = self.read_pos()  # query valve
        if pos == "B":
            self.state = DIMState.LOAD
        elif pos == "A":
            self.state = DIMState.INJECT
        else:
            self.state = DIMState.UNKNOWN
    
        if self.state != DIMState.LOAD:
            raise RuntimeError(
                f"DIM must be in LOAD to accept liquid. "
                f"Current valve position: {pos}, internal state: {self.state}"
            )

    def assert_inject(self, dry_run=False, trace=None):
        """
        Ensure the DIM is in INJECT (A) position.
        Sync internal state with hardware before asserting.
        """
        if dry_run:
            append_trace(trace, step="dim", action="assert_inject", module="dim")
            if self.state != DIMState.INJECT:
                raise RuntimeError(
                    f"DIM must be in INJECT to launch flow. "
                    f"Internal state: {self.state}"
                )
            return

        pos = self.read_pos()  # query valve
        if pos == "B":
            self.state = DIMState.LOAD
        elif pos == "A":
            self.state = DIMState.INJECT
        else:
            self.state = DIMState.UNKNOWN
    
        if self.state != DIMState.INJECT:
            raise RuntimeError(
                f"DIM must be in INJECT to launch flow. "
                f"Current valve position: {pos}, internal state: {self.state}"
            )
