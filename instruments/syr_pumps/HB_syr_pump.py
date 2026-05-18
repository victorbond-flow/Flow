import serial
import time
from core.flow_logging import FlowLogger
from core.tracing import append_trace

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
    def command(self, code, verbose=False):

        full_cmd = f"{code}\r"
        self.ser.write(full_cmd.encode("ascii"))
    
        time.sleep(0.1)
    
        response = []
    
        timeout = time.time() + 1
    
        while time.time() < timeout:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode().strip()
                response.append(line)
            else:
                break

        # Only print if explicitly requested (verbose = True)
        if verbose:
            print(f"Sent: {code} | Reply:")
            for line in response:
                print(line)
        
        return response

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

    def set_irate(self, rate_ml_min):
        """
        Set infusion rate for HB Elite.
        rate_ml_min: float, in mL/min
        """
        return self.command(f"irate {rate_ml_min} ml/min")

    def set_wrate(self, rate_ml_min):
        """
        Set withdrawal rate for HB Elite.
        rate_ml_min: float, in mL/min
        """
        return self.command(f"wrate {rate_ml_min} ml/min")

    def set_target_volume(self, vol):
        return self.command(f"tvolume {vol} ul")

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def infuse(self, dry_run=False, trace=None):
        if dry_run:
            append_trace(trace, step="syringe_pump", action="infuse")
            return []
        return self.command("irun")

    def withdraw(self, dry_run=False, trace=None):
        if dry_run:
            append_trace(trace, step="syringe_pump", action="withdraw")
            return []
        return self.command("wrun")

    def stop(self, dry_run=False, trace=None):
        if dry_run:
            append_trace(trace, step="syringe_pump", action="stop")
            return []
        return self.command("stop")

    def clear_volume(self):
        self.command("cvolume")
        self.command("ctvolume")

    # ------------------------------------------------------------------
    # Higher level methods
    # ------------------------------------------------------------------
    def infuse_volume(self, volume_ul, rate_ml_min, dry_run=False, trace=None):
        """
        Infuse a given volume (µL) at a given rate (mL/min)
        """
        if dry_run:
            append_trace(
                trace,
                step="syringe_pump",
                action="infuse_volume",
                volume_uL=volume_ul,
                rate=rate_ml_min,
            )
            return []

        self.clear_volume()                  # reset the pump memory
        self.set_irate(rate_ml_min)          # set infusion rate
        self.set_target_volume(volume_ul)    # use the correct variable
        self.infuse()                        # start infusion

    def withdraw_volume(self, volume_ul, rate_ml_min, dry_run=False, trace=None):
        if dry_run:
            append_trace(
                trace,
                step="syringe_pump",
                action="withdraw_volume",
                volume_uL=volume_ul,
                rate=rate_ml_min,
            )
            return []

        self.clear_volume()
        self.set_wrate(rate_ml_min)
        self.set_target_volume(volume_ul)
        self.withdraw()
