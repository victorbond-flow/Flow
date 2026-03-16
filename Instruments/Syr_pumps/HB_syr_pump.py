import serial
import datetime
import re
import time

def log_action(filename, data):
    """ Logging activity of equipment in an ongoing .txt file to allow for easier identification of errors that may occur """
    #Adding a timestamp in the format DD/MM/YYYY hh:mm:ss
    timestamp = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")
    #filename and 'a' for append mode(add not make new)
    with open('device_log.txt', 'a') as file:
        #added in the format [timestamp] + log information
        file.write(f'[{timestamp}] {data}\n')

class HBElite :
    
    def __init__(self, serial):
        self.ser = serial

    def connect(self): 
        """"" Connection of the valve to the computer via serial port """
        # Verifies that the serial connection is open
        if self.ser.isOpen():
            # Sets a timeout of 1 second for serial connection
            self.ser.timeout = 1
            print("Device is connected")
            log_action('device_log.txt', "Connection to HB pump successful.")

        else:
            # If port not open, displays port name and logs failure
            print ('The Port is closed: ' + self.ser.portstr)
            log_action('device_log.txt', "Connection to HB pump failed.")
    


    def command(self, code):
        """ Sends command to device in bytes, retrieves the response and adds to the activity log the relevant command """
        # Sends the command to the syringe pump
        self.ser.write(f'{code}\r'.encode())
        
        # Without this, the return does not match the executed code but the code previously executed
        time.sleep(0.1)
        
        # Initializes a list to hold the returned data
        response = []
        
        # Set a timeout for reading (1 seconds)
        timeout = time.time() + 1  # Timeout after 1 seconds (adjust as needed)
        
        # Read multiple lines of data from the syringe pump
        while time.time() < timeout:
            # If there is data available
            if self.ser.in_waiting > 0:
                # Reads one line of data
                byte_data = self.ser.readline().decode().strip() 

                # Optional logging built in
                if byte_data == '<':
                    log_action('device_log.txt', "Pump withdrawing.")

                elif byte_data == '>':
                    log_action('device_log.txt', "Pump infusing.")

                elif byte_data == 'T*':
                    log_action('device_log.txt', "Target volume reached.")

                # Adds to reponse list    
                response.append(byte_data) 
            else:
                # Exits if no more data available
                break

        # Returns reponse
        return response
            
        # Join the list of responses into a single string with newlines
        formatted_response = '\n'.join(response)  # Combine lines into a single string
        
        # Print the formatted response
        print(formatted_response)

    def read(self):
        """
        Reads any available response from the syringe pump.
        Returns:
            str or None: The line read from the pump (e.g. '<', '>', 'T*', or other messages),
                         or None if no data is available.
        """
        if self.ser.in_waiting > 0:
            byte_data = self.ser.readline().decode().strip()
    
            if byte_data == '<':
                log_action('device_log.txt', "Pump withdrawing.")
            elif byte_data == '>':
                log_action('device_log.txt', "Pump infusing.")
            elif byte_data == 'T*':
                log_action('device_log.txt', "Target volume reached.")
            elif byte_data != '':
                print(f'Pump says: {byte_data}')
    
            return byte_data
        else:
            return None

    def set_wrate(self, flow_rate):
        """ Sends  command string to set withdrawal rate as the given argument flow_rate """
        self.command(f'wrate {flow_rate}')
        log_action('device_log.txt', f'Syringe pump withdrawal rate has been set to {flow_rate}.')

    def set_irate(self, flow_rate):
        """ Sends  command string to set infusion rate as the given argument flow_rate """
        self.command(f'irate {flow_rate}')
        log_action('device_log.txt', f'Syringe pump infusion rate has been set to {flow_rate}.')

    def get_irate(self):
        """ Sends  command string to request information on infusion rate """
        flow_rate = self.command('irate')
        log_action('device_log.txt', 'Syringe pump infusion rate has been requested.')

    def get_wrate(self):
        """ Sends  command string to request information on infusion rate """
        flow_rate = self.command('wrate')
        log_action('device_log.txt', 'Syringe pump withdrawal rate has been requested.')

    def withdraw(self, tvolume=None):
        """ Sets target volume to be picked up, if no target volume given as argument or not previously stated, pump will withdraw until told to stop """
        if tvolume is not None:
            self.command(f'tvolume {tvolume}')
            log_action('device_log.txt', f"The syringe pump's target volume has been set to {tvolume}.")
            self.command(f'wrun')
            wrate = self.get_wrate()
            time.sleep(60 * (tvolume/wrate))
            self.command('stop')
            log_action('device_log.txt', f"{tvolume} has been withdrawn.")

        else:
            self.command('wrun')
            log_action('device_log.txt', 'Syringe pump has been set to withdraw.')
    
    def infuse(self):
        """ Sets target volume to be dispensed, if no target volume given as argument or not previously stated, pump will dispense until told to stop """
        self.command('irun')
        log_action('device_log.txt', 'Syringe pump has been set to infuse.')

    def set_tvolume(self, tvolume):
        """ Sets target volume to be picked up or dispensed """
        self.command(f'tvolume {tvolume}')
        log_action('device_log.txt', f"The syringe pump's target volume has been set to {tvolume}.")

    def clear_volume(self):
        """ Clears volume and target volume """
        self.command('cvolume')
        self.command('ctvolume')

    def stop(self):
        """ Stops withdrawal or infusion """
        self.command('stop')