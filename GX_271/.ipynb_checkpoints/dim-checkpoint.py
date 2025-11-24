import serial

class ViciValco:
    def __init__(self, port="COM6", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.meanings = {"A": "load", "B": "inject"}

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
        """Move to position A or B, and print functional meaning."""
        ser = self.ser
    
        # Read current position
        ser.write(b'CP\r')
        byteData = ser.readline().decode()
        position = byteData[-2]
    
        if position != pos:
            if pos == 'A':
                ser.write(b'CW\r')
            elif pos == 'B':
                ser.write(b'CC\r')
    
            meaning = self.meanings.get(pos, "")
            print(f"Valve moved to position {pos} ({meaning} position)")
        else:
            meaning = self.meanings.get(pos, "")
            print(f"Valve already at {pos} ({meaning} position)")


    def read_pos(self):
        """Read actual valve position, return A/B, print meaning."""
        ser = self.ser
        ser.write(b'CP\r')
        byteData = ser.readline().decode()
        pos = byteData[-2]
        meaning = self.meanings.get(pos, "unknown")
        print(f"Valve currently at {pos} ({meaning} position)")
    
        return pos


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
