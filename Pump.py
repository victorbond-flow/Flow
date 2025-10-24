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
        """Send command and print pump reply"""
        self.ser.write(f"{code}\r".encode())
        time.sleep(0.2)
        response = self.ser.readline().decode(errors='ignore').strip()
        print(f"Sent: {code} | Reply: {response}")
        return response

    