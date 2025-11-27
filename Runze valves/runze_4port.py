import serial
import time

# Special control characters for OEM protocol
STX = 0x02  # Start of text
ETX = 0x03  # End of text

class Runze4Port:
    """
    Minimal controller for a 4-port Runze MRV-01BM valve via RS-485.

    High-level helpers:
        select_position1() -> switches valve to position 1 (ports 1↔2, 3↔4)
        select_position2() -> switches valve to position 2 (ports 1↔3, 2↔4)
        toggle_position()  -> switches between position 1 and 2
    """

    # Map logical position names to valve positions
    LOGICAL_POSITIONS = {
        "position1": 1,
        "position2": 2,
    }

    def __init__(self, port="COM9", baudrate=9600, valve_address=1, timeout=1):
        """
        Initialize the valve object (does NOT open serial port yet).

        Arguments:
            port          : COM port string, e.g. "COM10"
            baudrate      : communication speed (9600 or 38400)
            valve_address : hardware address of the valve on the RS-485 bus
            timeout       : serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.valve_address = valve_address
        self.timeout = timeout
        self.ser = None
        self.seq_number = 1  # sequence number (kept simple)

        # Tracks last commanded logical position
        self.current_position = None

    def connect(self):
        """
        Open the serial port and connect to the valve.
        Must be called before sending any commands.
        """
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout
        )
        if self.ser.is_open:
            print(f"Connected to Runze 4-port valve on {self.port}")
        else:
            raise Exception("Could not open serial port")

    def calc_checksum(self, data_bytes):
        """
        Calculate an 8-bit checksum for the message.
        The valve uses this to detect transmission errors.
        """
        return sum(data_bytes) % 256

    def _send_command(self, command_str):
        """
        Internal helper: send a command string with OEM framing.
        Frame = STX + valve address + seq number + ASCII command + ETX + checksum
        """
        data_block = command_str.encode("ascii")
        frame = bytearray()
        frame.append(STX)
        frame.append(self.valve_address)
        frame.append(self.seq_number)
        frame.extend(data_block)
        frame.append(ETX)
        checksum = self.calc_checksum(frame[1:])  # exclude STX
        frame.append(checksum)

        self.ser.write(frame)
        time.sleep(0.05)  # small delay for valve processing

    def _read_response(self, max_bytes=255):
        """
        Internal helper: read raw bytes from the valve.
        Returns bytes (may need parsing to interpret).
        """
        return self.ser.read(max_bytes)

    # ----------------------------
    # Low-level valve operations
    # ----------------------------

    def move_clockwise(self, position: int):
        """
        Move valve clockwise to a specific position.
        Executes immediately.
        """
        cmd = f"I{position}R"  # I<n> = clockwise, R = execute
        self._send_command(cmd)
        self.current_position = position

    def move_counterclockwise(self, position: int):
        """
        Move valve counterclockwise to a specific position.
        Executes immediately.
        """
        cmd = f"O{position}R"  # O<n> = counterclockwise, R = execute
        self._send_command(cmd)
        self.current_position = position

    # ----------------------------
    # High-level logical helpers
    # ----------------------------

    def select_position1(self):
        """
        Switch valve to position 1 (ports 1↔2, 3↔4).
        """
        self.move_clockwise(self.LOGICAL_POSITIONS["position1"])
        print("Valve set to POSITION 1")

    def select_position2(self):
        """
        Switch valve to position 2 (ports 1↔3, 2↔4).
        """
        self.move_clockwise(self.LOGICAL_POSITIONS["position2"])
        print("Valve set to POSITION 2")

    def toggle_position(self):
        """
        Toggle between position 1 and position 2.
        """
        if self.current_position == self.LOGICAL_POSITIONS["position1"]:
            self.select_position2()
        else:
            self.select_position1()

    def read_position(self):
        """
        Query the valve for its current position.
        Returns raw bytes from the valve (needs parsing for human-readable status).
        """
        self._send_command("?6")
        resp = self._read_response()
        return resp
