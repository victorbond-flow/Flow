from enum import Enum, auto
from core.logging import flow_logger as logger, log_call
from core.tracing import append_trace
import serial


class FSMState(Enum):
    GAS_TO_DIM = auto()
    CARRIER_TO_DIM = auto()
    UNKNOWN = auto()


class FSM:
    """
    Controller for VICI 6-port, 2-position valve (Runze replacement).

    - Same semantic role as Runze62Valve
    - Uses VICI ASCII protocol (CW/CC, CP)
    - State is derived from hardware (not assumed)
    """

    def __init__(self, port="COM2", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.ser = None
        self.state = FSMState.UNKNOWN

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @log_call
    def connect(self):
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=self.timeout
        )

        if not self.ser.is_open:
            raise RuntimeError("Could not open serial port")

        print(f"Connected to FSM on {self.port}")

        # Sync state on connect
        self._sync_state()

    # ------------------------------------------------------------------
    # Public API (same as Runze)
    # ------------------------------------------------------------------

    def read_pos(self) -> str:
        """Return 'A' or 'B' from valve."""
        resp = self._send("CP")
        if len(resp) < 1:
            return "?"
        return resp[-1]

    @log_call
    def go_to_pos(self, pos: str, dry_run=False, trace=None):
        """Move valve to 'A' or 'B'."""
        pos = pos.upper()

        # Determine semantic state (UPDATED MAPPING)
        if pos == "A":
            new_state = FSMState.GAS_TO_DIM
        elif pos == "B":
            new_state = FSMState.CARRIER_TO_DIM
        else:
            raise ValueError("Position must be 'A' or 'B'")

        if dry_run:
            self.state = new_state
            append_trace(
                trace,
                step="fsm",
                action="go_to_pos",
                notes=pos,
            )
            if trace is None:
                print(f"[FSM] Dry-run valve to {pos} -> state = {self.state.name}")
            return

        current = self.read_pos()

        # Sync current state
        self._sync_state()

        if current == pos:
            if trace is None:
                print(f"[FSM] Already at {pos} -> state = {self.state.name}")
            return

        # Perform move
        if pos == "A":
            self._send("CW")
        elif pos == "B":
            self._send("CC")

        # Update state
        self.state = new_state

        if trace is None:
            print(f"[FSM] Valve moved to {pos} -> state = {self.state.name}")

    @log_call
    def toggle(self):
        current = self.read_pos()

        if current == "A":
            self.go_to_pos("B")
        elif current == "B":
            self.go_to_pos("A")
        else:
            raise RuntimeError("Unknown valve position")

    # --- Semantic wrappers ---

    @log_call
    def gas_to_dim(self, dry_run=False, trace=None):
        """Route gas to DIM (now position A)."""
        append_trace(trace, step="fsm", action="gas_to_dim")
        self.go_to_pos("A", dry_run=dry_run, trace=trace)

    @log_call
    def carrier_to_dim(self, dry_run=False, trace=None):
        """Route carrier to DIM (now position B)."""
        append_trace(trace, step="fsm", action="carrier_to_dim")
        self.go_to_pos("B", dry_run=dry_run, trace=trace)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_state(self):
        pos = self.read_pos()

        if pos == "A":
            self.state = FSMState.GAS_TO_DIM
        elif pos == "B":
            self.state = FSMState.CARRIER_TO_DIM
        else:
            self.state = FSMState.UNKNOWN

    def _send(self, cmd: str) -> str:
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port not open")

        self.ser.write((cmd + "\r").encode("ascii"))
        resp = self.ser.readline().decode(errors="ignore")
        return resp.strip()
