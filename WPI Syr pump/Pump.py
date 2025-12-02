import datetime
import serial
import re
import time

class AL1000:
    STATUS_MAP = {
        "I": "Infusing",
        "W": "Withdrawing",
        "S": "Pumping Program Stopped",
        "P": "Pumping Program Paused",
        "T": "Timed Pause Phase",
        "U": "Operational Trigger Wait"
    }

    ALARM_MAP = {
        "R": "Pump was reset (power interruption)",
        "S": "Pump motor stalled",
        "T": "Safe mode communications timeout",
        "E": "Pumping Program error",
        "O": "Pumping Program Phase is out of range"
    }

    ERROR_MAP = {
        "?": "Command not recognized",
        "NA": "Command not applicable",
        "OOR": "Command data out of range",
        "COM": "Invalid communications packet received",
        "IGN": "Command ignored due to simultaneous new Phase start"
    }

    def __init__(self, ser, device_address="@00", sleep_time=0.5):
        """
        ser: an opened pyserial Serial object
        device_address: string, e.g., '@00' for pump address
        sleep_time: seconds to wait after sending a command
        """
        self.ser = ser
        self.device_address = device_address
        self.sleep_time = sleep_time

    def connect(self):
        """Check connection to pump via serial port"""
        if self.ser.isOpen():
            self.ser.timeout = 1
            print("Device is connected")
        else:
            print("The Port is closed:", self.ser.portstr)

    def _parse_response(self, raw: bytes):
        """Parse raw pump response into human-readable English"""
        if not raw:
            return "No response"

        # Remove STX/ETX
        if raw.startswith(b'\x02'):
            raw = raw[1:]
        if raw.endswith(b'\x03'):
            raw = raw[:-1]

        text = raw.decode('ascii', errors='replace').strip()

        # Check for system command (*)
        sys_cmd = text.startswith("*")
        address = None
        status = None
        data = None

        # Split into address + rest
        if len(text) >= 2 and text[0:2].isdigit():
            address = text[0:2]
            rest = text[2:]
        else:
            rest = text

        # Check if it's an alarm
        if rest.startswith("A?"):
            alarm_code = rest[2:] if len(rest) > 2 else ""
            alarm_msg = self.ALARM_MAP.get(alarm_code, f"Unknown alarm: {alarm_code}")
            return f"Alarm [{alarm_code}]: {alarm_msg}"

        # Check for errors
        if rest in self.ERROR_MAP:
            return f"Error: {self.ERROR_MAP[rest]}"

        # Status code
        if rest and rest[0] in self.STATUS_MAP:
            status = self.STATUS_MAP[rest[0]]
            data = rest[1:].strip() if len(rest) > 1 else None
        else:
            data = rest

        if data:
            return f"{status if status else 'Status'} | Data: {data}"
        else:
            return f"{status if status else 'Status only'}"

    def command(self, code, use_splat=True):
        """Send a command to the pump and return parsed response"""
        cmd_prefix = "*" if use_splat else ""
        full_cmd = f"{self.device_address}{cmd_prefix}{code}\r"

        self.ser.write(full_cmd.encode('ascii'))
        time.sleep(self.sleep_time)

        raw = self.ser.read(64)
        parsed = self._parse_response(raw)

        print(f"Sent: {full_cmd.strip()} | Reply: {raw} | Parsed: {parsed}")
        return parsed

    #----------------------------------------
    # Helper methods
    #----------------------------------------
    def start(self):
        return self.command("STT")

    def stop(self):
        return self.command("STP")

    def set_rate(self, rate):
        return self.command(f"RAT{rate}")

    def set_direction(self, direction):
        return self.command(f"DIR{direction}")  # 'INF' or 'WDR'

    def set_volume(self, volume):
        return self.command(f"VOL{volume}")

    def set_diameter(self, dia):
        return self.command(f"DIA{dia}")

    def get_diameter(self):
        return self.command("DIA")  # query command

    def identify(self):
        return self.command("ID")   # pump identification

    def firmware(self):
        return self.command("VER", use_splat=True)

    def reset(self):
        return self.command("RESET", use_splat=True)


    