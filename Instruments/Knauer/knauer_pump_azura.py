import datetime
import serial
import re
import time
from Core.flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

class KnauerPumpAzura:
    def __init__(self, ser):
        self.ser = ser

    @log_call
    def connect(self):
        """Open serial port and check connection."""
        if self.ser.is_open:
            self.ser.timeout = 1
            print(f"Connected to Azura pump on {self.ser.port}")
        else:
            raise RuntimeError(f"Port {self.ser.port} is closed")

    def command(self, code):
        """Sends command to device in bytes and retrieves the response."""
        self.ser.write(f'{code}\r'.encode())
        byteData = self.ser.readline().decode().strip()
        return byteData

    def get_sernum(self):
        byteData = self.command("SERNUM?")
        return byteData

    @log_call
    def set_flow_rate(self, flow_rate):
        """Set the flow rate in uL/min."""
        byteData = self.command(f"FLOW:{flow_rate}")
        if byteData == "OK":
            print(f"[k_pump] Flow rate set to {flow_rate} uL/min")
        return byteData

    def get_flow_rate(self):
        byteData = self.command("FLOW?")
        return byteData

    @log_call
    def start_flow(self):
        byteData = self.command("ON")
        if byteData == "OK":
            print("[Pump] Flow started")
        return byteData

    @log_call
    def stop_flow(self):
        byteData = self.command("OFF")
        if byteData == "OK":
            print("[Pump] Flow stopped")
        return byteData
    