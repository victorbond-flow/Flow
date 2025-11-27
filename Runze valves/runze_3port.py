import serial
import time

# These are special control characters used in the OEM protocol
STX = 0x02  # Start of text (marks the beginning of a command)
ETX = 0x03  # End of text (marks the end of a command)

class Runze3Port:
    """
    Minimal controller for a 3-port Runze MRV-01BM valve via RS-485.

    High-level helpers:
        select_carrier()  -> switches the valve so carrier liquid flows to outlet
        select_nitrogen() -> switches the valve so nitrogen gas flows to outlet
        toggle_flow()     -> switches between carrier and nitrogen
    """

    # Map logical flow names to physical valve positions
    # "carrier" -> position 1 on the valve
    # "nitrogen" -> position 2 on the valve
    LOGICAL_PORTS = {
        "carrier": 1,   # valve connects carrier inlet to outlet
        "nitrogen": 2,  # valve connects nitrogen inlet to outlet
    }

    def __init__(self, port="COM9", baudrate=9600, valve_address=1, timeout=1):
        """
        Initialize the valve object. Does NOT open serial port yet.

        Arguments:
            port          : COM port string, e.g. "COM9"
            baudrate      : communication speed (9600 or 38400)
            valve_address : hardware address of the valve on the RS-485 bus
            timeout       : serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.valve_address = valve_address
        self.timeout = timeout
        self.ser = None  # will hold the serial port object
        self.seq_number = 1  # sequence number for protocol (kept simple)

        # Tracks the last logical position we commanded the valve to
        self.current_port = None

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
            print(f"Connected to Runze valve on {self.port}")
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
        Internal helper: Send a command to the valve with proper OEM framing.

        OEM framing = STX + valve address + sequence number + ASCII command + ETX + checksum
        """
        # Convert command string to ASCII bytes
        data_block = command_str.encode("ascii")

        # Build the full message frame
        frame = bytearray()
        frame.append(STX)                # start marker
        frame.append(self.valve_address) # valve address
        frame.append(self.seq_number)    # sequence number
        frame.extend(data_block)         # command string
        frame.append(ETX)                # end marker
        checksum = self.calc_checksum(frame[1:])  # calculate checksum (exclude STX)
        frame.append(checksum)           # append checksum

        # Send to the valve over serial
        self.ser.write(frame)

        # Wait a short time for valve to process command
        time.sleep(0.05)

    def _read_response(self, max_bytes=255):
        """
        Internal helper: Read raw bytes from the valve.
        Returns whatever the valve sends back (may need parsing).
        """
        return self.ser.read(max_bytes)

    # ----------------------------
    # Low-level valve operations
    # ----------------------------

    def move_clockwise(self, port: int):
        """
        Move valve clockwise to a specific position.
        Executes immediately.
        """
        cmd = f"I{port}R"  # I<n> = move clockwise, R = execute
        self._send_command(cmd)
        self.current_port = port

    def move_counterclockwise(self, port: int):
        """
        Move valve counterclockwise to a specific position.
        Executes immediately.
        """
        cmd = f"O{port}R"  # O<n> = move counterclockwise, R = execute
        self._send_command(cmd)
        self.current_port = port

    # ----------------------------
    # High-level logical helpers
    # ----------------------------

    def select_carrier(self):
        """
        Switch valve so the carrier liquid inlet flows to the outlet.
        """
        self.move_clockwise(self.LOGICAL_PORTS["carrier"])
        print("Valve set to CARRIER")

    def select_nitrogen(self):
        """
        Switch valve so the nitrogen gas inlet flows to the outlet.
        """
        self.move_clockwise(self.LOGICAL_PORTS["nitrogen"])
        print("Valve set to NITROGEN")

    def toggle_flow(self):
        """
        Toggle between carrier and nitrogen flows.
        If last commanded flow was carrier -> switch to nitrogen.
        If last commanded flow was nitrogen -> switch to carrier.
        """
        if self.current_port == self.LOGICAL_PORTS["carrier"]:
            self.select_nitrogen()
        else:
            self.select_carrier()

    def read_position(self):
        """
        Query the valve for its current position.
        Returns raw bytes from the valve (needs parsing to interpret).
        """
        self._send_command("?6")
        resp = self._read_response()
        return resp


