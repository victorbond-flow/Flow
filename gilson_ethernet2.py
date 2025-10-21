import socket
import time
import xml.etree.ElementTree as ET

class GilsonSession:
    """
    A class to manage a session with a Gilson Ethernet-controlled device.
    Handles connection, command formatting, sending, and response parsing.
    """
# When the code runs g = GilsonSession('192.168.x.x'), this function automatically connects to the Gilson,   sets up internal variables, and sends a handshake command
    def __init__(self, ip, admin_port=50185):
        self.ip = ip
        self.admin_port = admin_port
        self.session_port = None
        self.session_socket = None
        self.sequence_number = 40
        self._connect()
        self.send_admin_command()
        self.Z_SAFE = 175
        self.current_z = 0
        
# This function connects to the Gilsons admin port. The Gilson replies with a different port number where it'll handle commands, the script opens that second connection and stores it as self.session_socket
    def _connect(self):
        message = "<Gilson><GilsonConnect>Gilson Ethernet Utility</GilsonConnect></Gilson>"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((self.ip, self.admin_port))
            s.sendall(message.encode('ascii'))
            response = s.recv(4096).decode('ascii')

        if "<ParameterName>ResponseValue</ParameterName>" in response:
            port = int(response.split("<ParameterValue>")[2].split("</ParameterValue>")[0])
            self.session_port = port

            self.session_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.session_socket.settimeout(2)
            self.session_socket.connect((self.ip, self.session_port))
        else:
            raise RuntimeError("Failed to retrieve assigned session port from Gilson.")
            
# This method takes an XML command (such as move the probe) and sends it to the Gilson. It waits up to 0.5s for a reply - If it finds a valid XML response, it hands that to _parse_response() for decoding, otherwise you get the error message
    def send_raw_command(self, xml_payload, expected_command=None):
        try:
            self.session_socket.sendall(xml_payload.encode('ascii'))
            buffer = b""
            start_time = time.time()
            while time.time() - start_time < 0.5:
                try:
                    self.session_socket.settimeout(0.05)
                    part = self.session_socket.recv(8192)
                    if part:
                        buffer += part
                    else:
                        break
                except socket.timeout:
                    continue

            responses = buffer.decode('ascii', errors='ignore')
            messages = responses.split("</Message>")
            for msg in messages:
                msg = msg.strip()
                if not msg:
                    continue
                msg += "</Message>" if not msg.endswith("</Message>") else ""
                if expected_command:
                    if f"<CommandName>{expected_command}</CommandName>" in msg and "<Response>" in msg:
                        return self._parse_response(msg)
                else:
                    if "<Response>" in msg:
                        return self._parse_response(msg)
            return "No valid response received."
        except Exception as e:
            return f"Error sending raw command: {e}"
            
# This is the response interpreter - it turns the returned XML response from the Gilson into a readable summary. If the XML can't be read, it returns an error message
    def _parse_response(self, xml_message):
        try:
            root = ET.fromstring(xml_message)
            command_name = root.findtext(".//CommandName")
            parameters = root.findall(".//ReturnParameter")
            if not parameters:
                parameters = root.findall(".//Parameter")
            values = []
            for param in parameters:
                name = param.findtext("ParameterName")
                value = param.findtext("ParameterValue")
                if name and value:
                    values.append(f"{value}")
            return f"{command_name}: {', '.join(values)}" if values else command_name
        except ET.ParseError:
            return "Failed to parse response."
            
# When a command is sent, the following code issues the "next ticket number" - the Gilson uses it to match replies to certain commands.
    def _get_next_sequence_number(self):
        self.sequence_number += 1
        return self.sequence_number
        
#
    def make_command(self, command_name, device="GX-27x", device_id=35, sequence_number=None, command_type="Local", parameters=None):
        if sequence_number is None:
            sequence_number = self._get_next_sequence_number()

        param_xml = ""
        if parameters:
            param_xml = "<Parameters>"
            for key, value in parameters.items():
                param_xml += f"<Parameter><ParameterName>{key}</ParameterName><ParameterValue>{value}</ParameterValue></Parameter>"
            param_xml += "</Parameters>"

        xml = f"""
<Gilson>
  <CommandData>
    <Commands>
      <Command>
        <CommandType>{command_type}</CommandType>
        <CommandInfo>
          <InstrumentInfo>
            <DeviceName>{device}</DeviceName>
            <DeviceId>{device_id}</DeviceId>
          </InstrumentInfo>
          <SequenceNumber>{sequence_number}</SequenceNumber>
          <Synchronize>True</Synchronize>
          <Selected>False</Selected>
          <CommandXML>
            <CommandName>{command_name}</CommandName>
            {param_xml}
          </CommandXML>
        </CommandInfo>
      </Command>
    </Commands>
  </CommandData>
</Gilson>"""
        return xml.strip()

    def send_command(self, command_name, device="GX-27x", device_id=35, sequence_number=None, parameters=None):
        xml = self.make_command(command_name, device, device_id, sequence_number, command_type="Local", parameters=parameters)
        return self.send_raw_command(xml, expected_command=command_name)

    def send_immediate_command(self, command_name, device="GX-27x", device_id=35, sequence_number=None, parameters=None):
        xml = self.make_command(command_name, device, device_id, sequence_number, command_type="Immediate", parameters=parameters)
        return self.send_raw_command(xml, expected_command=command_name)

    def send_admin_command(self):
        xml = """
<Gilson>
  <CommandData>
    <Commands>
      <Command>
        <CommandType>Local</CommandType>
        <CommandInfo>
          <InstrumentInfo>
            <DeviceName>System</DeviceName>
            <DeviceId>-1</DeviceId>
          </InstrumentInfo>
          <SequenceNumber>0</SequenceNumber>
          <Synchronize>True</Synchronize>
          <Selected>False</Selected>
          <CommandXML>
            <CommandName>Admin</CommandName>
          </CommandXML>
        </CommandInfo>
      </Command>
    </Commands>
  </CommandData>
</Gilson>"""
        return self.send_raw_command(xml.strip(), expected_command="Admin")
    

    def move_x(self, position):
        if self.current_z < self.Z_SAFE:
            print(f"Z below safe limit ({self.current_z:.2f} < {self.Z_SAFE:.2f}) — raising first.")
            self.move_z(self.Z_SAFE)
            
        parameters = {"X Position": position}
        result = self.send_command("Move X", parameters=parameters)
        return f"Moved X to {position}. Result: {result}"

    def move_y(self, position):
        if self.current_z < self.Z_SAFE:
            print(f"Z below safe limit ({self.current_z:.2f} < {self.Z_SAFE:.2f}) — raising first.")
            self.move_z(self.Z_SAFE)
            
        parameters = {"Y Position": position}
        result = self.send_command("Move Y", parameters=parameters)
        return f"Moved Y to {position}. Result: {result}"

    def move_z(self, position):
        """Move Z to target, respecting lower and upper limits."""
    
        # Clamp to safe range
        if position < self.Z_SAFE:
            print(f"⚠️ Requested Z={position} below safe minimum ({self.Z_SAFE} mm). Clamping.")
            position = self.Z_SAFE
        elif position > self.Z_MAX_SAFE:
            print(f"⚠️ Requested Z={position} above safe maximum ({self.Z_MAX_SAFE} mm). Clamping.")
            position = self.Z_MAX_SAFE

        parameters = {"Z Position": position}
        result = self.send_command("Move Z", parameters=parameters)
        self.current_z = position
        return f"Moved Z to {position}. Result: {result}"


    def move_xy(self, x_position, y_position):
        if self.current_z < self.Z_SAFE:
            print(f"Z below safe limit ({self.current_z:.2f} < {self.Z_SAFE:.2f}) — raising first.")
            self.move_z(self.Z_SAFE)
            
        parameters = {
            "X Position": x_position,
            "Y Position": y_position
        }
        result = self.send_command("Move XY", parameters=parameters)
        return f"Moved to X={x_position}, Y={y_position}. Result: {result}"
    
    def home(self):
        self.send_command("Home")
        print("All axes homed successfully")

    def close(self):
        if self.session_socket:
            self.session_socket.close()
            self.session_socket = None
