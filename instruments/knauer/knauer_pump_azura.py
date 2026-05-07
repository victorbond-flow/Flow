import datetime
import serial
import re
import time
from core.flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

class KnauerPumpAzura:
    def __init__(self, port="COM3", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    @log_call
    def connect(self):
        """Open serial port and check connection."""
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout
        )
    
        if self.ser.is_open:
            print(f"Connected to Azura pump on {self.port}")
        else:
            raise RuntimeError(f"Could not open port {self.port}")

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
        print(f"[k_pump] Flow rate set to {flow_rate} uL/min")
        return byteData

    def get_flow_rate(self):
        byteData = self.command("FLOW?")
        return byteData

    @log_call
    def start_flow(self):
        byteData = self.command("ON")
        print("[Pump] Flow started")
        return byteData

    @log_call
    def stop_flow(self):
        byteData = self.command("OFF")
        print("[Pump] Flow stopped")
        return byteData
    