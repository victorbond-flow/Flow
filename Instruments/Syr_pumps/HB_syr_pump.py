import serial
import time
from Core.flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call


class HBElite:
    """
    Harvard Bioscience Elite Syringe Pump Driver
    """

    def __init__(self, port="COM2", baudrate=115200, sleep_time=0.1):
        self.port = port
        self.baudrate = baudrate
        self.sleep_time = sleep_time
        self.ser = None

    # ------------------------------------------------------------------
    # Core connection
    # ------------------------------------------------------------------

    @log_call
    def connect(self):
        """Open the serial port."""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=1
        )

        if self.ser.is_open:
            print(f"HB Elite pump connected on {self.port}")
        else:
            raise RuntimeError(f"Could not open port {self.port}")

    # ------------------------------------------------------------------
    # Low-level command
    # ------------------------------------------------------------------

    @log_call
    def command(self, code):
        """
        Send a raw command to the pump and return the reply.
        """
        full_cmd = f"{code}\r"

        self.ser.write(full_cmd.encode("ascii"))
        time.sleep(self.sleep_time)

        raw = self.ser.readline()

        if not raw:
            print(f"Sent: {code} | Reply: <none>")
            return None

        decoded = raw.decode("ascii", errors="replace").strip()

        print(f"Sent: {code} | Reply: {decoded}")

        return decoded

    # ------------------------------------------------------------------
    # Status reader (important for Elite pumps)
    # ------------------------------------------------------------------

    def read_status(self):
        """
        Non-blocking read of pump status characters.
        """
        if self.ser.in_waiting:
            msg = self.ser.readline().decode().strip()

            if msg == "<":
                return "withdrawing"

            elif msg == ">":
                return "infusing"

            elif msg == "T*":
                return "target_reached"

            return msg

        return None

    # ------------------------------------------------------------------
    # Get commands
    # ------------------------------------------------------------------

    def get_irate(self):
        return self.command("irate")

    def get_wrate(self):
        return self.command("wrate")

    def get_target_volume(self):
        return self.command("tvolume")

    # ------------------------------------------------------------------
    # Set commands
    # ------------------------------------------------------------------

    def set_irate(self, rate):
        return self.command(f"irate {rate}")

    def set_wrate(self, rate):
        return self.command(f"wrate {rate}")

    def set_target_volume(self, vol):
        return self.command(f"tvolume {vol}")

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def infuse(self):
        return self.command("irun")

    def withdraw(self):
        return self.command("wrun")

    def stop(self):
        return self.command("stop")

    def clear_volume(self):
        self.command("cvolume")
        self.command("ctvolume")