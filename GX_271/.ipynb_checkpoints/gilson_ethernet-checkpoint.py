import socket
import time
import xml.etree.ElementTree as ET
from rack_commands import Rackcommands
from flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

#############################################################################################
# gilson_ethernet.py
# -------------------------------------------------------------------------------------------
# High-level interface for controlling a Gilson autosampler over Ethernet.
#
# Responsibilities:
#   - Connect to the Gilson device via its admin port and retrieve a session port
#   - Manage a persistent session socket for sending and receiving commands
#   - Construct properly formatted XML commands for the autosampler
#   - Send commands (Local or Immediate) and parse XML responses into readable output
#   - Track the current Z-axis position and enforce safety limits globally or per rack
#   - Maintain a collection of Rackcommands instances for one or more racks
#
# Features:
#   - High-level methods g.go_to_vial() and g.move_into_vial() delegate to the correct Rackcommands
#   - Z-axis safety enforces working_min, safe, and max_safe heights
#   - Rack-specific limits override global defaults where defined
#   - Supports adding racks dynamically with add_rack()
#   - Low-level access through send_command(), send_immediate_command(), and send_raw_command()
#
# Relationships:
#   - Uses Rackcommands to handle probe movements for individual racks
#   - Rackcommands relies on rack geometry and vial positions to compute XY coordinates
#   - Z-safety and movement logic respect both global defaults and rack-specific overrides
#
# Notes:
#   - The session automatically tracks sequence numbers for command matching
#   - The class separates session management, command construction, and movement logic
#   - Intended as the main user-facing interface for automated experiments
#############################################################################################


class GilsonEthernet:
    """
    A class to manage a session with a Gilson Ethernet-controlled device.
    Handles connection, command formatting, sending, and response parsing.
    """

    # When the code runs g = GilsonEthernet('192.168.x.x'), this function automatically connects to the Gilson,   sets up internal variables, and sends a handshake command
    def __init__(self, ip, admin_port=50185):
        self.ip = ip
        self.admin_port = admin_port
        self.session_port = None
        self.session_socket = None
        self.sequence_number = 40
        self._connect()
        self.send_admin_command()

        # Keep track of racks - Key = rack number, value = Rackcommands instance
        self.racks = {}

        # Z safety / position
        self.Z_SAFE = 45
        self.Z_MAX_SAFE = 120
        self.Z_WORKING_MIN = 11
        self.current_z = self.Z_SAFE

    # This function connects to the Gilsons admin port. The Gilson replies with a different port number where it'll handle commands, the script opens that second connection and stores it as self.session_socket
    def _connect(self):
        message = (
            "<Gilson><GilsonConnect>Gilson Ethernet Utility</GilsonConnect></Gilson>"
        )

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((self.ip, self.admin_port))
            s.sendall(message.encode("ascii"))
            response = s.recv(4096).decode("ascii")

        if "<ParameterName>ResponseValue</ParameterName>" in response:
            port = int(
                response.split("<ParameterValue>")[2].split("</ParameterValue>")[0]
            )
            self.session_port = port

            self.session_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.session_socket.settimeout(2)
            self.session_socket.connect((self.ip, self.session_port))
        else:
            raise RuntimeError("Failed to retrieve assigned session port from Gilson.")

    # This method takes an XML command (such as move the probe) and sends it to the Gilson. It waits up to 0.5s for a reply - If it finds a valid XML response, it hands that to _parse_response() for decoding, otherwise you get the error message
    def send_raw_command(self, xml_payload, expected_command=None):
        try:
            self.session_socket.sendall(xml_payload.encode("ascii"))
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

            responses = buffer.decode("ascii", errors="ignore")
            messages = responses.split("</Message>")
            for msg in messages:
                msg = msg.strip()
                if not msg:
                    continue
                msg += "</Message>" if not msg.endswith("</Message>") else ""
                if expected_command:
                    if (
                        f"<CommandName>{expected_command}</CommandName>" in msg
                        and "<Response>" in msg
                    ):
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

    # This command constructs the XML block required for a Gilson command
    def make_command(
        self,
        command_name,
        device="GX-27x",
        device_id=35,
        sequence_number=None,
        command_type="Local",
        parameters=None,
    ):
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

    def send_command(
        self,
        command_name,
        device="GX-27x",
        device_id=35,
        sequence_number=None,
        parameters=None,
    ):
        xml = self.make_command(
            command_name,
            device,
            device_id,
            sequence_number,
            command_type="Local",
            parameters=parameters,
        )
        return self.send_raw_command(xml, expected_command=command_name)

    def send_immediate_command(
        self,
        command_name,
        device="GX-27x",
        device_id=35,
        sequence_number=None,
        parameters=None,
    ):
        xml = self.make_command(
            command_name,
            device,
            device_id,
            sequence_number,
            command_type="Immediate",
            parameters=parameters,
        )
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

    ##########################################################################################################################################################
    ##### -------------------------------------------------- HELPER COMMANDS ----------------------------------------------------------------------------#####
    ##########################################################################################################################################################

    @log_call
    def move_x(self, position):
        z_safe = self.Z_SAFE
        if rack_num and rack_num in self.racks:
            z_safe = self.racks[rack_num].z_limits["safe"]

        if self.current_z < z_safe:
            print(
                f"Z below safe limit ({self.current_z:.2f} < {z_safe:.2f}) — raising first."
            )
            self.move_z(z_safe, rack_num=rack_num)

        parameters = {"X Position": position}
        result = self.send_command("Move X", parameters=parameters)
        return f"Moved X to {position}. Result: {result}"

    @log_call
    def move_y(self, position):
        z_safe = self.Z_SAFE
        if rack_num and rack_num in self.racks:
            z_safe = self.racks[rack_num].z_limits["safe"]

        if self.current_z < z_safe:
            print(
                f"Z below safe limit ({self.current_z:.2f} < {z_safe:.2f}) — raising first."
            )
            self.move_z(z_safe, rack_num=rack_num)

        parameters = {"Y Position": position}
        result = self.send_command("Move Y", parameters=parameters)
        return f"Moved Y to {position}. Result: {result}"

    @log_call
    def move_z(self, position, allow_in_vial=True, rack_num=None):
        """Move the Z-axis to the specified height.


        Z-axis movements enforce strict limits:
        - working_min: the lowest allowed height inside a vial
        - safe: the minimum safe height for horizontal motion
        - max_safe: the upper safe limit

        Behaviour:
        - If moving inside a vial (allow_in_vial=True), drooping too low is
        clamped to the vial's working minimum.
        - If allow_in_vial=False, Z cannot go below the safe height at all.
        - If a rack_num is supplied, rack-specific limits override the globals."""

        if rack_num is not None:
            if rack_num not in self.racks:
                raise ValueError(f"No rack at position {rack_num}")
            z_limits = self.racks[rack_num].z_limits
        else:
            z_limits = {
                "safe": self.Z_SAFE,
                "max_safe": self.Z_MAX_SAFE,
                "working_min": self.Z_WORKING_MIN,
            }

        if allow_in_vial:
            if position < z_limits["working_min"]:
                print(
                    f"⚠️ Requested Z={position} below working minimum ({z_limits['working_min']} mm). Clamping."
                )
                position = z_limits["working_min"]
            elif position > z_limits["max_safe"]:
                print(
                    f"⚠️ Requested Z={position} above safe maximum ({z_limits['max_safe']} mm). Clamping."
                )
                position = z_limits["max_safe"]
        else:
            if position < z_limits["safe"]:
                print(
                    f"⚠️ Requested Z={position} below safe height ({z_limits['safe']} mm). Clamping to safe."
                )
                position = z_limits["safe"]
            elif position > z_limits["max_safe"]:
                print(
                    f"⚠️ Requested Z={position} above safe maximum ({z_limits['max_safe']} mm). Clamping."
                )
                position = z_limits["max_safe"]

        parameters = {"Z Position": position}
        result = self.send_command("Move Z", parameters=parameters)
        self.current_z = position
        return f"Moved Z to {position}. Result: {result}"

    @log_call
    def move_xy(self, x_position, y_position, rack_num=None):
        z_safe = self.Z_SAFE
        if rack_num is not None and rack_num in self.racks:
            z_safe = self.racks[rack_num].z_limits["safe"]

        if self.current_z < z_safe:
            print(
                f"Z below safe limit ({self.current_z:.2f} < {z_safe:.2f}) — raising first."
            )
            self.move_z(z_safe, rack_num=rack_num)

        parameters = {"X Position": x_position, "Y Position": y_position}
        result = self.send_command("Move XY", parameters=parameters)
        return f"Moved to X={x_position}, Y={y_position}. Result: {result}"

    @log_call
    def home(self):
        # Ensure Z is at least safe before homing X/Y
        if self.current_z < self.Z_SAFE:
            print(
                f"Z below safe limit ({self.current_z:.2f} < {self.Z_SAFE:.2f}) — raising first."
            )
            self.move_z(self.Z_SAFE)

        # Send home command
        self.send_command("Home")

        # Immediately move Z to your max safe height
        if self.current_z > self.Z_MAX_SAFE:
            print(
                f"Z exceeded max safe height ({self.current_z:.2f} > {self.Z_MAX_SAFE:.2f}) — lowering to safe max."
            )
        self.move_z(self.Z_MAX_SAFE)

        print("All axes homed successfully and Z is within safe limits")

    def get_error(self):
        # Reads the error number and describes the error
        return self.send_command("Get Error")

    def clear_error(self):
        # Clears error state
        return self.send_command("Clear Error")

    def status(self):
        # Returns XYZ position, motor status, and error if any
        return self.send_command("Get Status")

    def reset(self):
        # Resets the autosampler
        return self.send_command("Reset")

    def add_rack(self, rack_obj, rack_position=1):
        # Add a rack object manually to the session
        if rack_position in self.racks:
            print(f"⚠️ Rack position {rack_position} already has a rack, overwriting.")

        self.racks[rack_position] = Rackcommands(
            self, rack_obj, rack_position=rack_position
        )

        # Show the rack class name in the output
        rack_name = type(rack_obj).__name__
        print(f"Rack '{rack_name}' added at position {rack_position}.")

    @log_call
    def go_to_vial(self, vial_pos, rack_num=1):
        """High-level wrapper for vial navigation.

        This method does NOT compute coordinates or move the hardware directly.
        Instead, it selects the correct rack (via rack_num) and then delegates
        the actual movement to Rackcommands.go_to_vial() for that rack."""

        if rack_num not in self.racks:
            raise ValueError(f"No rack at position {rack_num}")
        return self.racks[rack_num].go_to_vial(vial_pos)

    @log_call
    def go_into_vial(self, rack_num=1):
        """
        High-level wrapper for lowering into a vial.

        This method selects which rack is being operated on (rack_num), then
        hands off the actual Z-movement to Rackcommands.move_into_vial()."""

        if rack_num not in self.racks:
            raise ValueError(f"No rack at position {rack_num}")
        target_z = self.racks[rack_num].z_limits["working_min"]
        return self.racks[rack_num].go_into_vial()

    def close(self):
        if self.session_socket:
            self.session_socket.close()
            self.session_socket = None

### ---------- TESTING CODE ON GX-241 --------------- ###

    def send_gsioc(self, command, unit_id=30):
        # GSIOC messages: /<unitID><command><CR>
        msg = f"/{unit_id}{command}\r"
        self.session_socket.sendall(msg.encode("ascii"))
        time.sleep(0.2)
        response = self.session_socket.recv(4096).decode("ascii", errors="ignore")
        return response
