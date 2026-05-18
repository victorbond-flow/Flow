import datetime
import serial
import re
import time
from core.flow_logging import FlowLogger
from core.tracing import append_trace

logger = FlowLogger()
log_call = logger.log_call

class KnauerPumpS100:
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
            print(f"Connected to Knauer pump on {self.port}")
        else:
            raise RuntimeError(f"Could not open port {self.port}")

    @log_call
    def command(self, code):
        """ Sends command to device in bytes and retrieves the response """
        #sending the command to device
        self.ser.write(f'{code}\r'.encode())
        #accepting the response
        byteData = self.ser.readline().decode().strip()
        #give response
        return byteData

    def get_version(self):
        byteData = self.command("V?")
        return byteData
    
    @log_call
    def set_flow_rate(self, flow_rate, dry_run=False, trace=None):
        if dry_run:
            append_trace(
                trace,
                step="carrier_pump",
                action="set_flow_rate",
                volume_uL=flow_rate,
                notes="uL/min",
            )
            print(f"[k_pump] Dry-run flow rate set to {flow_rate} uL/min")
            return None

        byteData = self.command(f"F{int(flow_rate)}")
        if byteData == "OK":
            print(f"[k_pump] Flow rate set to {flow_rate} uL/min")
        return byteData
        
    def get_flow_rate(self):
        byteData = self.command("F?")
        return byteData
        print('Flow rate set to {byteData} ml/min.')

    @log_call
    def start_flow(self, dry_run=False, trace=None):
        if dry_run:
            append_trace(trace, step="carrier_pump", action="start_flow")
            print("[Pump] Dry-run flow started")
            return None
        byteData = self.command('M1')
        if byteData == "OK":
            print("[Pump] Flow started")
        return byteData

    @log_call
    def stop_flow(self, dry_run=False, trace=None):
        if dry_run:
            append_trace(trace, step="carrier_pump", action="stop_flow")
            print("[Pump] Dry-run flow stopped")
            return None
        byteData = self.command('M0')
        if byteData == "OK":
            print("[Pump] Flow stopped")
        return byteData
