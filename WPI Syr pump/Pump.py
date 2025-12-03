import serial
import time

class AL1000:
    def __init__(self, ser, device_address="@00", sleep_time=0.5, use_splat=True):
        """
        ser: opened pyserial Serial object
        device_address: string, e.g., '@00' for pump address
        sleep_time: seconds to wait after sending a command
        use_splat: whether to prepend '*' to commands for system-level
        """
        self.ser = ser
        self.device_address = device_address
        self.sleep_time = sleep_time
        self.use_splat = use_splat

    # -----------------------------
    # Core methods
    # -----------------------------
    def connect(self):
        if self.ser.isOpen():
            self.ser.timeout = 1
            print("Device is connected")
        else:
            print("Port is closed:", self.ser.portstr)

    def command(self, code):
        """Send a command and read raw response."""
        cmd_prefix = "*" if self.use_splat else ""
        full_cmd = f"{self.device_address}{cmd_prefix}{code}\r"
        self.ser.write(full_cmd.encode('ascii'))
        time.sleep(self.sleep_time)
        raw = self.ser.read(64)
        if not raw:
            return None
        if raw.startswith(b'\x02'):
            raw = raw[1:]
        if raw.endswith(b'\x03'):
            raw = raw[:-1]
        response = raw.decode('ascii', errors='replace').strip()
        print(f"Sent: {full_cmd.strip()} | Reply: {raw} | Parsed: {self._parse_response(response)}")
        return response

    def _parse_response(self, response):
        """Return a tuple: (status in english, error if any, data if any)"""
        if not response:
            return ("No response", None, None)

        # Status is first character
        status_map = {
            "I": "Infusing",
            "W": "Withdrawing",
            "S": "Pumping Program Stopped",
            "P": "Pumping Program Paused",
            "T": "Timed Pause Phase",
            "U": "Operational trigger wait (user wait)",
            "A": "Alarm"
        }
        status_char = response[0]
        status = status_map.get(status_char, "Unknown Status")

        # Check for error markers in response
        error = None
        data = None
        if "?" in response:
            error = "Command not recognized or invalid data"
            data = response[1:] if len(response) > 1 else None
        elif len(response) > 1:
            data = response[1:]

        return status, error, data

    # -----------------------------
    # Helper methods
    # -----------------------------
    def identify(self):
        return self.command("VER")

    def get_diameter(self):
        return self.command("DIA")

    def set_diameter(self, dia):
        return self.command(f"DIA{dia}")

    def set_rate(self, rate):
        """Always RAT C <rate> MM (mL/min)"""
        return self.command(f"RAT C {rate} MM")

    def get_rate(self):
        return self.command("RAT")

    def set_volume(self, volume):
        return self.command(f"VOL{volume}")

    def get_volume(self):
        return self.command("VOL")

    def set_direction(self, direction):
        """direction: INF, WDR, REV, STK"""
        return self.command(f"DIR{direction}")

    def get_direction(self):
        return self.command("DIR")

    def get_status(self):
        """
        Return a full snapshot of the pump's current state:
        phase, rate, volume, direction, status byte.
        """
        phase = self.command("PHN")
        rate  = self.get_rate()
        vol   = self.get_volume()
        direc = self.get_direction()
    
        # Raw status is the first byte of any response (S, I, W, A...)
        status = None
        if rate:
            parsed = self._parse_response(rate)
            status = parsed[0]  # English status
    
        return {
            "status": status,
            "phase": phase,
            "rate": rate,
            "volume": vol,
            "direction": direc
        }


    # -----------------------------
    # Program Phase helpers
    # -----------------------------
    def select_phase(self, phase=1):
        """
        Select a Pumping Program Phase in non-volatile memory.
        All subsequent set commands modify that Phase.
        """
        return self.command(f"PHN{phase}")

    # -----------------------------
    # Start/Stop
    # -----------------------------
    def start(self):
        """
        Clean, correct start:
        RUN <phase>
        """
        return self.command("RUN 1")   # Phase 1 always

    def stop(self):
        return self.command("STP")

    # -----------------------------
    # Prepare method
    # -----------------------------
    def prepare(self, dia, rate, volume, direction):
        """
        Program Phase 1 with DIA, RAT, VOL, DIR.
        These values are stored in NVM and used when RUN 1 is issued.
        """
        print("\n--- Preparing pump (Phase 1) ---")

        # 1) Select Phase 1 so all following commands modify it
        self.select_phase(1)

        # 2) Apply all settings *into Phase 1 memory*
        self.set_diameter(dia)
        self.get_diameter()

        self.set_rate(rate)
        self.get_rate()

        self.set_volume(volume)
        self.get_volume()

        self.set_direction(direction)
        self.get_direction()

        print("--- Preparation complete ---\n")







    