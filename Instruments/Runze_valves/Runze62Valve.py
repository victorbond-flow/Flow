import serial
import time
from typing import Tuple


class Runze62Valve:
    """
    Controller for Runze SV-07B 6-port, 2-position valve via RS-232.

    Position is software-tracked and guaranteed by:
    - verified ACK/status from controller
    - deterministic homing on connect()
    """

    STX = 0xCC
    ETX = 0xDD

    # --- Common command codes ---
    CMD_SWITCH = 0x44
    CMD_QUERY_STATUS = 0x4A
    CMD_QUERY_VERSION = 0x3F

    STATUS_OK = 0x00
    STATUS_BUSY = 0xFE

    def __init__(self, port="COM7", baudrate=9600, timeout=1, address=0x00):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.address = address

        self.ser = None
        self._position = None  # software-tracked position (1 or 2)

    # ------------------------------------------------------------------
    # Connection & homing
    # ------------------------------------------------------------------

    def connect(self):
        """Open serial port and home valve to position 1."""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=self.timeout,
        )

        if not self.ser.is_open:
            raise RuntimeError("Could not open serial port")

        print(f"Connected to Runze valve on {self.port}")

        # Home deterministically
        self.go_to_pos(1)

    # ------------------------------------------------------------------
    # Public valve API 
    # ------------------------------------------------------------------

    def read_pos(self) -> int:
        """
        Return current valve position (1 or 2).

        Note: This is software-tracked, not hardware-queried.
        """
        if self._position is None:
            raise RuntimeError("Valve position unknown (not homed)")
        return self._position

    def go_to_pos(self, pos: int):
        """Move valve to position 1 or 2."""
        if pos not in (1, 2):
            raise ValueError("Position must be 1 or 2")

        if self._position == pos:
            print(f"Valve already at position {pos}")
            return

        self._send_switch_command(pos)
        self._position = pos

        print(f"Valve moved to position {pos}")

    def toggle(self):
        """Toggle between position 1 and 2."""
        if self._position is None:
            raise RuntimeError("Valve position unknown (not homed)")

        new_pos = 2 if self._position == 1 else 1
        self.go_to_pos(new_pos)

    # ------------------------------------------------------------------
    # Internal protocol handling
    # ------------------------------------------------------------------

    def _send_switch_command(self, position: int):
        """Send validated switch command and confirm success."""
        params = (position, 0x00)
        self._send_and_confirm(self.CMD_SWITCH, params)

    def _send_and_confirm(self, cmd: int, params: Tuple[int, int]):
        """Send a common command and validate response."""
        frame = self._build_common_frame(cmd, params)
        self._write(frame)

        response = self._read_response()
        self._validate_response(response)

    # ------------------------------------------------------------------
    # Frame handling
    # ------------------------------------------------------------------

    def _build_common_frame(self, cmd: int, params: Tuple[int, int]) -> bytes:
        b0 = self.STX
        b1 = self.address
        b2 = cmd
        b3, b4 = params
        b5 = self.ETX

        checksum = self._checksum([b0, b1, b2, b3, b4, b5])
        return bytes([b0, b1, b2, b3, b4, b5, checksum & 0xFF, checksum >> 8])

    def _checksum(self, data):
        """Runze sumcheck: sum of bytes B0–B5."""
        return sum(data) & 0xFFFF

    # ------------------------------------------------------------------
    # Serial I/O
    # ------------------------------------------------------------------

    def _write(self, frame: bytes):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port not open")

        self.ser.write(frame + b"\r\n")

    def _read_response(self) -> bytes:
        resp = self.ser.read(8)
        if len(resp) != 8:
            raise RuntimeError(f"Incomplete response: {resp.hex()}")
        return resp

    # ------------------------------------------------------------------
    # Response validation
    # ------------------------------------------------------------------

    def _validate_response(self, resp: bytes):
        b0, b1, status, b3, b4, b5, _, _ = resp

        if b0 != self.STX or b5 != self.ETX:
            raise RuntimeError(f"Invalid frame markers: {resp.hex()}")

        if b1 != self.address:
            raise RuntimeError(f"Address mismatch in response: {resp.hex()}")

        if status == self.STATUS_OK:
            return

        if status == self.STATUS_BUSY:
            raise RuntimeError("Valve reports motor busy")

        raise RuntimeError(f"Valve error (status 0x{status:02X})")

    # ------------------------------------------------------------------
    # Optional diagnostics
    # ------------------------------------------------------------------

    def query_version(self) -> Tuple[int, int]:
        """Return firmware version (major, minor)."""
        frame = self._build_common_frame(self.CMD_QUERY_VERSION, (0x01, 0x00))
        self._write(frame)

        resp = self._read_response()
        self._validate_response(resp)

        _, _, _, major, minor, _, _, _ = resp
        return major, minor
