import serial
from Core.logging import flow_logger as logger, log_call

class DIM:
    """
    Minimal controller for a 2-position Vici Cheminert valve (A/B) via RS-232.
    """

    def __init__(self, port="COM9", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

        # --- Relative geometry (tray applies global offsets) ---
        self.offset_x = 0.0
        self.offset_y = 0.0

        # --- Z limits ---
        self.z_limits = {
            "safe": 130.0,
            "max_safe": 130.0,
            "working_min": 120    # To be determined!
        }
        

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
            print(f"Connected to Vici valve on {self.port}")
        else:
            raise Exception("Could not open serial port")

    def _send(self, cmd: str) -> str:
        """
        Internal helper to send ASCII commands with \r and return decoded response.
        """
        if not self.ser or not self.ser.is_open:
            raise Exception("Serial port not open")

        self.ser.write((cmd + "\r").encode("ascii"))
        return self.ser.readline().decode(errors="ignore").strip()

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

        if current == pos:
            print(f"Valve already at {pos}")
            return

        if pos == "A":
            self._send("CW")
        elif pos == "B":
            self._send("CC")
        else:
            raise ValueError("Position must be 'A' or 'B'")

        print(f"Valve moved to {pos}")

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

