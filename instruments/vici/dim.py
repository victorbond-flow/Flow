import serial
from enum import Enum, auto
from core.logging import flow_logger as logger, log_call

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
    def go_to_pos(self, pos: str):
        """
        Moves valve to 'A' or 'B'.
        A = CW   (clockwise)
        B = CC   (counter-clockwise)
        """
        pos = pos.upper()
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

    def load(self):
        """ Connects injection assay to sample loop """
        self.go_to_pos("B")

    def inject(self):
        """ Connects injection assay to waste (gas/solvent from Runze toward sample loop now) """
        self.go_to_pos("A")

    def assert_load(self):
        """
        Ensure the DIM is in LOAD (B) position.
        Sync internal state with hardware before asserting.
        """
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

    def assert_inject(self):
        """
        Ensure the DIM is in INJECT (A) position.
        Sync internal state with hardware before asserting.
        """
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
