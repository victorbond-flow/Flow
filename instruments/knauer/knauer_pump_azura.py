import datetime
import serial
import re
import time
from core.flow_logging import FlowLogger
from core.tracing import append_trace

logger = FlowLogger()
log_call = logger.log_call

class KnauerPumpAzura:
    def __init__(self, port="COM3", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.flow_rate_ul_min = None
        self.is_running = False

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
    def set_flow_rate(self, flow_rate, dry_run=False, trace=None):
        """Set the flow rate in uL/min."""
        if dry_run:
            self.flow_rate_ul_min = flow_rate
            append_trace(
                trace,
                step="carrier_pump",
                action="set_flow_rate",
                volume_uL=flow_rate,
                notes="uL/min",
            )
            print(f"[k_pump] Dry-run flow rate set to {flow_rate} uL/min")
            return None

        byteData = self.command(f"FLOW:{flow_rate}")
        self.flow_rate_ul_min = flow_rate
        print(f"[k_pump] Flow rate set to {flow_rate} uL/min")
        return byteData

    def get_flow_rate(self):
        byteData = self.command("FLOW?")
        return byteData

    @log_call
    def start_flow(self, dry_run=False, trace=None):
        if dry_run:
            self.is_running = True
            append_trace(trace, step="carrier_pump", action="start_flow")
            print("[Pump] Dry-run flow started")
            return None
        byteData = self.command("ON")
        self.is_running = True
        print("[Pump] Flow started")
        return byteData

    @log_call
    def stop_flow(self, dry_run=False, trace=None):
        if dry_run:
            self.is_running = False
            append_trace(trace, step="carrier_pump", action="stop_flow")
            print("[Pump] Dry-run flow stopped")
            return None
        byteData = self.command("OFF")
        self.is_running = False
        print("[Pump] Flow stopped")
        return byteData
