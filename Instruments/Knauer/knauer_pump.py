import datetime
import serial
import re
import time
from flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

class KnauerPump :
    def __init__(self, serial):
        self.ser = serial

    @log_call
    def connect(self): 
        """"" Connection of the valve to the computer via serial port """
        if self.ser.isOpen():
            self.ser.timeout = 1
            print("Device is connected")
        else:
            print ('The Port is closed: ' + self.ser.portstr)

    @log_call
    def command(self, code):
        """ Sends command to device in bytes and retrieves the response """
        #sending the command to device
        self.ser.write(f'{code}\r'.encode())
        #accepting the response
        byteData = self.ser.readline().decode().strip()
        #give response
        return byteData

    def get_sernum(self):
        byteData = self.command("SERNUM?")
        return byteData
    
    @log_call
    def set_flow_rate(self, flow_rate):
        byteData = self.command(f"FLOW:{flow_rate}")
        return byteData
        print('Flow rate set to {flow_rate} ul/min')

    def get_flow_rate(self):
        byteData = self.command("FLOW?")
        return byteData
        print('Flow rate set to {byteData} ml/min.')

    @log_call
    def start_flow(self):
        byteData = self.command('ON')
        return byteData
        print('Pump to begin flow.')

    @log_call
    def stop_flow(self):
        byteData = self.command('OFF')
        return byteData
        print('Pump to stop flow.')