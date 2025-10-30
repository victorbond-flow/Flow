import datetime
import serial
import re
import time

class AL1000:
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

    def command(self, code):
        """Send a command to the pump and read the response."""
        full_cmd = f"@00{code}\r"
        self.ser.write(full_cmd.encode())
        time.sleep(1)  # may need 1–2 s for slower commands
        time.sleep(0.2)  # allow pump to respond
        raw = self.ser.read_until(b'\x03')  # read until ETX (0x03)
        if raw.startswith(b'\x02'):  # strip STX/ETX if present
            raw = raw[1:]
        if raw.endswith(b'\x03'):
            raw = raw[:-1]
        print("Raw bytes:", raw)
        response = raw.decode('ascii', errors='replace').strip()

        print(f"Sent: {full_cmd.strip()} | Reply: {response}")
        return response



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

    