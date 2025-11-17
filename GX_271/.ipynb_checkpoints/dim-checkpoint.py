import serial

class ViciValco:
    def __init__(self, port="COM6", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        """Open serial connection."""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )

        if self.ser.is_open:
            print("Device is connected")
        else:
            raise RuntimeError("Failed to open serial port")

    def go_to_pos(self, pos):
        """Move valve to position A or B."""
        self.ser.write(b"CP\r")
        byteData = self.ser.readline().decode()
        position = byteData[-2] if len(byteData) >= 2 else None

        if position != pos:
            if pos == 'A':
                self.ser.write(b'CW\r')
                print("Valve moved to position A")
            elif pos == 'B':
                self.ser.write(b'CC\r')
                print("Valve moved to position B")
        else:
            print("Valve already at that position")

    def read_pos(self):
        """Return 'A' or 'B'."""
        self.ser.write(b"CP\r")
        byteData = self.ser.readline().decode()

        if len(byteData) >= 2:
            return byteData[-2]
        return None

    def change_pos(self):
        """Toggle between A and B."""
        pos = self.read_pos()

        if pos == "A":
            self.go_to_pos("B")
        elif pos == "B":
            self.go_to_pos("A")
        else:
            print("Unknown current position:", pos)

    def command(self, code):
        """Send raw command string."""
        if not self.ser or not self.ser.is_open:
            raise Exception("Serial port is not open")

        cmd = f"{code}\r".encode()
        self.ser.write(cmd)

        response = self.ser.readline().decode(errors="ignore")
        return response.strip()
