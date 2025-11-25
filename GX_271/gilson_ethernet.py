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

    def ensure_z_safe(self, module_name=None):
        """
        Ensures the probe is at a safe Z height before any horizontal move.
        
        If module_name is None:
            - Use GLOBAL limits (Z_SAFE, Z_MAX_SAFE).
        
        If module_name is provided:
            - Identify the module object from self.modules
            - Use module-specific safe height (module.z_limits["safe"])
            - BUT never exceed global Z_MAX_SAFE.
        """
    
        # --- 1) If module name provided, resolve module + check it exists ---
        if module_name is not None:
            if module_name not in self.modules:
                raise ValueError(f"Unknown module '{module_name}' passed to ensure_z_safe().")
    
            module = self.modules[module_name]
            module_safe = module.z_limits["safe"]     # e.g. 45 for Rack_209
            global_max = self.Z_MAX_SAFE
    
            # --- Need to lift? ---
            if self.current_z < module_safe:
                self.move_z(module_safe)
    
            # --- Need to clamp down (should be rare)? ---
            elif self.current_z > global_max:
                self.move_z(global_max)
    
            return  # done
    
    
        # --- 2) No module → GLOBAL safety rules ---
        global_safe = self.Z_SAFE
        global_max = self.Z_MAX_SAFE
    
        if self.current_z < global_safe:
            self.move_z(global_safe)
    
        elif self.current_z > global_max:
            self.move_z(global_max)

    
    @log_call
    def move_x(self, position, module_name=None):
        """
        Move the X-axis safely.
        If module_name is provided, module-specific Z safe limits are used.
        Otherwise, global Z safe limits are enforced.
        """
    
        # Enforce Z safety before moving horizontally
        self.ensure_z_safe(module_name)
    
        parameters = {"X Position": position}
        result = self.send_command("Move X", parameters=parameters)
    
        return f"Moved X to {position}. Result: {result}"



    @log_call
    def move_y(self, position, module_name=None):
        """
        Move the Y-axis safely.
        If module_name is provided, module-specific Z safe limits are used.
        Otherwise, global Z safe limits are enforced.
        """
    
        # Enforce Z safety before moving horizontally
        self.ensure_z_safe(module_name)
    
        parameters = {"Y Position": position}
        result = self.send_command("Move Y", parameters=parameters)
    
        return f"Moved Y to {position}. Result: {result}"



    @log_call
    def move_z(self, position, allow_in_vial=True, module_name=None):
        """
        Move the Z-axis safely, respecting either global or module-specific limits.
    
        Parameters
        ----------
        position : float
            The requested Z height.
        allow_in_vial : bool, default=True
            True  → vial operations allowed (use working_min)
            False → horizontal-safety move (use safe height)
        module_name : str, optional
            Use this module's Z limits if provided. Otherwise use global limits.
        """
    
        # ----------------------------------------------------------
        # 1. Choose Z limit set (module-specific or global)
        # ----------------------------------------------------------
        if module_name is not None:
            rack = self.tray.get_module(module_name)  # fail-fast if module doesn't exist
            z_limits = rack.z_limits
        else:
            z_limits = {
                "safe": self.Z_SAFE,
                "max_safe": self.Z_MAX_SAFE,
                "working_min": self.Z_WORKING_MIN,
            }
    
        safe_z       = z_limits["safe"]
        max_safe_z   = z_limits["max_safe"]
        working_min  = z_limits["working_min"]
    
        # ----------------------------------------------------------
        # 2. Clamp based on whether we're allowed to enter a vial
        # ----------------------------------------------------------
        original_position = position  # for diagnostics, if needed
    
        if allow_in_vial:
            # Inside a vial → use working_min as min bound
            if position < working_min:
                position = working_min
            elif position > max_safe_z:
                position = max_safe_z
        else:
            # Horizontal-safe move → use safe height as min bound
            if position < safe_z:
                position = safe_z
            elif position > max_safe_z:
                position = max_safe_z
    
        # ----------------------------------------------------------
        # 3. Execute the movement
        # ----------------------------------------------------------
        parameters = {"Z Position": position}
        result = self.send_command("Move Z", parameters=parameters)
        self.current_z = position
    
        return f"Moved Z to {position}. Result: {result}"



    @log_call
    def move_xy(self, x_position, y_position, module_name=None):
        """
        Move both X and Y axes safely in one operation.
        If module_name is provided, module-specific Z safe limits are used.
        Otherwise, global Z safe limits are enforced.
        """
    
        # Enforce Z safety before moving horizontally
        self.ensure_z_safe(module_name)
    
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

    
    @log_call
    def go_to_vial(self, module_name: str, vial_pos: int, send=True):
        """
        Move the probe to the given vial inside a module.
        
        Safety model:
        - Before ANY horizontal move, raise to module-specific safe Z
          (via ensure_z_safe(module_name)).
        - Movement is global XY coordinates (Tray handles offsets).
        """
    
        # ----------------------------------------------------------
        # 1. Resolve module + coordinates
        # ----------------------------------------------------------
        rack = self.tray.get_module(module_name)        # fail-fast if unknown
        off_x, off_y = self.tray.get_offsets(module_name)
        x_rel, y_rel = rack.get_vial_coordinates(vial_pos)
    
        x = off_x + x_rel
        y = off_y + y_rel
    
        # ----------------------------------------------------------
        # 2. Raise Z to rack-safe height before XY
        # ----------------------------------------------------------
        self.ensure_z_safe(module_name=module_name)
    
        # ----------------------------------------------------------
        # 3. Return only (for debugging)
        # ----------------------------------------------------------
        if not send:
            return x, y
    
        # ----------------------------------------------------------
        # 4. Move XY with module-specific Z safety active
        # ----------------------------------------------------------
        print(f"Moving to {module_name} vial {vial_pos} at ({x:.2f}, {y:.2f}) mm")
        self.move_xy(x, y, module_name=module_name)
    
        return x, y



    @log_call
    def go_into_vial(self, module_name: str, vial_pos: int, send=True):
        """
        Move the Gilson probe into a specific vial of a module.
    
        Parameters
        ----------
        module_name : str
            Name of the module as registered in Tray.add_module().
        vial_pos : int
            Vial number within that module.
        send : bool, optional
            If False, just return coordinates without moving.
    
        Returns
        -------
        (x, y, z) : tuple of floats
            Absolute coordinates on the tray, including Z at working_min.
        """
    
        # --- get module object from tray ---
        rack = self.tray.get_module(module_name)
    
        # --- get tray/global offsets ---
        off_x, off_y = self.tray.get_offsets(module_name)
    
        # --- get vial coordinates relative to rack origin ---
        x_rel, y_rel = rack.get_vial_coordinates(vial_pos)
    
        # --- compute absolute coordinates ---
        x_abs = off_x + x_rel
        y_abs = off_y + y_rel
    
        # If only computing, stop here
        if not send:
            return x_abs, y_abs, rack.z_limits["working_min"]
    
        # ----------------------------
        # Step 1: go over the vial
        # (this calls move_xy → ensure_z_safe automatically)
        # ----------------------------
        self.go_to_vial(module_name, vial_pos, send=True)
    
        # ----------------------------
        # Step 2: descend to working_min
        # (move_z clamps and checks limits automatically)
        # ----------------------------
        z_working = rack.z_limits["working_min"]
        self.move_z(z_working, module_name=module_name)
    
        return x_abs, y_abs, z_working




    def close(self):
        if self.session_socket:
            self.session_socket.close()
            self.session_socket = None
