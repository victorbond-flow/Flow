from enum import Enum, auto
from core.logging import flow_logger as logger, log_call
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
    def go_to_pos(self, pos: str):
        """Move valve to 'A' or 'B'."""
        pos = pos.upper()
        current = self.read_pos()

        # Determine semantic state (UPDATED MAPPING)
        if pos == "A":
            new_state = FSMState.GAS_TO_DIM
        elif pos == "B":
            new_state = FSMState.CARRIER_TO_DIM
        else:
            raise ValueError("Position must be 'A' or 'B'")

        # Sync current state
        self._sync_state()

        if current == pos:
            print(f"[FSM] Already at {pos} -> state = {self.state.name}")
            return

        # Perform move
        if pos == "A":
            self._send("CW")
        elif pos == "B":
            self._send("CC")

        # Update state
        self.state = new_state

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
    def gas_to_dim(self):
        """Route gas to DIM (now position A)."""
        self.go_to_pos("A")

    @log_call
    def carrier_to_dim(self):
        """Route carrier to DIM (now position B)."""
        self.go_to_pos("B")

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