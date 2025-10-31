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
        """Send a command to the pump and read the ASCII response."""
        # Basic Mode: no STX/length/CRC needed, just device address + code + CR
        full_cmd = f"{self.device_address}{code}\r"
        self.ser.write(full_cmd.encode('ascii'))
        time.sleep(self.sleep_time)
    
        # Read raw response
        raw = self.ser.read(64)  # adjust buffer size if needed
        if not raw:
            return "No response"
    
        # Strip STX/ETX if present
        if raw.startswith(b'\x02'):
            raw = raw[1:]
        if raw.endswith(b'\x03'):
            raw = raw[:-1]
    
        # Decode ASCII safely
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

    