import datetime
import serial
import re
import time

class AL1000:
    def __init__(self, serial):
        self.ser = serial

    def connect(self): 
        """"" Connection of the valve to the computer via serial port """
        if self.ser.isOpen():
            self.ser.timeout = 1
            print("Device is connected")
            #log_action('device_log.txt', "Connection to Knauer pump successful.")

        else:
            print ('The Port is closed: ' + self.ser.portstr)
            #log_action('device_log.txt', "Connection to Knauer pump failed.")
        
    def command(self, code):
        """ Sends command to device in bytes and retrieves the response """
        #sending the command to device
        self.ser.write(f'{code}\r'.encode())
        #accepting the response
        #byteData = self.ser.readline().decode().strip()
        #give response
        #return byteData