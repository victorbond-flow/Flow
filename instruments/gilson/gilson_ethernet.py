import socket
import time
import xml.etree.ElementTree as ET
from core.logging import flow_logger as logger, log_call

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
    def __init__(self, ip, admin_port=50185, tray=None):
        self.ip = ip
        self.admin_port = admin_port
        self.session_port = None
        self.session_socket = None
        self.sequence_number = 40
        self.tray = tray
    
        # --- Connect to hardware ---
        self._connect()
        self.send_admin_command()
    
        # --- Keep track of racks ---
        self.racks = {}
    
        # --- Global Z safety constants ---
        self.Z_SAFE = 127
        self.Z_MAX_SAFE = 127
        self.Z_WORKING_MIN = 1
    
        # --- Probe state (unknown until synced) ---
        self.current_x = None
        self.current_y = None
        self.current_z = None
        self.current_module = None
    
        # --- Sync python state to hardware ---
        self.sync_hardware_state()


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

    def sync_hardware_state(self):
        """
        Sync Python-side probe state with the hardware.
    
        Uses:
        - "Get Z Position" for Z
        - "Get XY Position" for X and Y
    
        Raises RuntimeError if any axis cannot be read.
    
        Sets:
        - self.current_x, self.current_y, self.current_z
        - self.current_module if probe is physically inside a module
        """
    
        # --- Query Z ---
        z_resp = self.send_command("Get Z Position")
        try:
            self.current_z = float(z_resp.split(":")[1].strip())
        except Exception as e:
            raise RuntimeError(f"Unable to read Z position from response: '{z_resp}'") from e
    
        # --- Query XY ---
        xy_resp = self.send_command("Get XY Position")
        try:
            xy_part = xy_resp.split(":")[1].strip()  # e.g., '201, 39'
            x_str, y_str = xy_part.split(",")
            self.current_x = float(x_str.strip())
            self.current_y = float(y_str.strip())
        except Exception as e:
            raise RuntimeError(f"Unable to read XY position from response: '{xy_resp}'") from e
    
        # --- Determine current module based on XY + Z ---
        module = self.tray.get_module_at_xy(self.current_x, self.current_y)
        if module is not None and self.current_z < module.z_limits["safe"]:
            self.current_module = module.module_id
        else:
            self.current_module = None



        
        
    def ensure_z_safe(self, destination_module=None):
        """
        Ensure the probe is at a safe Z height before any horizontal move.
        
        Lifts only if needed to clear the current module (if any) and/or the
        destination module. Falls back to global Z_SAFE if neither module applies.
        """
        # Compute the required clearance
        target_z = self.required_z_clearance(destination_module)
    
        # Only move Z if we're below the target
        if self.current_z < target_z:
            self.move_z(target_z)
        else:
            # Already above everything, no movement needed
            print(f"[DEBUG] ensure_z_safe: current_z={self.current_z} is already >= target_z={target_z}")





    def required_z_clearance(self, destination_module=None):
        """
        Compute the minimum Z height required before any XY motion.
    
        Rules:
        - Must clear the module we're currently inside (if any)
        - Must clear the destination module (if any)
        - If neither exists, use global Z_SAFE as a fallback
        - Never exceed Z_MAX_SAFE
        """
        required_z = 0.0  # start with “no reference”
    
        # Current module clearance
        if self.current_module is not None:
            current = self.tray.get_module(self.current_module)
            required_z = max(required_z, current.z_limits["safe"])
    
        # Destination module clearance
        if destination_module is not None:
            dest = self.tray.get_module(destination_module)
            required_z = max(required_z, dest.z_limits["safe"])
    
        # Fallback to global safe if nothing else
        if required_z == 0.0:
            required_z = self.Z_SAFE
    
        # Hard ceiling
        if required_z > self.Z_MAX_SAFE:
            raise RuntimeError(
                f"Required Z clearance ({required_z}) exceeds hard limit ({self.Z_MAX_SAFE})"
            )
    
        return required_z



    
    @log_call
    def move_x(self, position, module_name=None):
        """
        Move the X-axis safely.
        Automatically computes required Z based on current module and
        the module at the target X position.
        """
        
        # --- Infer the destination module from target X/Y ---
        destination_module = self.tray.get_module_at_xy(position, self.current_y)
        
        # --- Update current_module based on current XY ---
        if self.tray is not None:
            current_module_name = self.tray.get_module_at_xy(self.current_x, self.current_y)
            slot = self.resolve_slot(module_name)
            self.current_module = self.tray.assigned_modules[slot]["module_id"]
        
        # --- Enforce Z safety before horizontal move ---
        self.ensure_z_safe(destination_module=destination_module)
        
        # --- Execute the move ---
        parameters = {"X Position": position}
        result = self.send_command("Move X", parameters=parameters)
        
        # --- Update Python-side state ---
        self.current_x = float(position)
        
        return f"Moved X to {position}. Result: {result}"





    @log_call
    def move_y(self, position, module_name=None):
        """
        Move the Y-axis safely.
        Automatically computes required Z based on current module and
        the module at the target X/Y position.
        """
        
        # --- Infer the destination module from target X/Y ---
        destination_module = self.tray.get_module_at_xy(self.current_x, position)
        
        # --- Update current_module based on current XY ---
        if self.tray is not None:
            current_module_name = self.tray.get_module_at_xy(self.current_x, self.current_y)
            self.current_module = module_name
        
        # --- Enforce Z safety before horizontal move ---
        self.ensure_z_safe(destination_module=destination_module)
        
        # --- Execute the move ---
        parameters = {"Y Position": position}
        result = self.send_command("Move Y", parameters=parameters)
        
        # --- Update Python-side state ---
        self.current_y = float(position)
        
        return f"Moved Y to {position}. Result: {result}"





    @log_call
    def move_z(self, position, speed=125, allow_in_vial=False, module_name=None):
        """
        Move the Z-axis to a given position at a specified speed, enforcing hard physical limits only.
    
        Parameters:
        - position: target Z position in mm
        - speed: Z-axis movement speed in mm/sec (default 125)
        - allow_in_vial: if True, allows movement below working_min
        - module_name: optional, restrict Z limits to a specific module
        """
        
        # ----------------------------------------------------------
        # 1. Choose Z limit set (module-specific or global)
        # ----------------------------------------------------------
        if module_name is not None:
            slot = self.resolve_slot(module_name)
            rack = self.tray.get_module(slot)
            z_limits = rack.z_limits
        else:
            z_limits = {
                "safe": self.Z_SAFE,
                "max_safe": self.Z_MAX_SAFE,
                "working_min": self.Z_WORKING_MIN,
            }
    
        max_safe_z  = z_limits["max_safe"]
        working_min = z_limits["working_min"]
    
        # ----------------------------------------------------------
        # 2. Enforce HARD bounds only
        # ----------------------------------------------------------
        if allow_in_vial and position < working_min:
            position = working_min
    
        if position > max_safe_z:
            raise RuntimeError(
                f"Requested Z ({position}) exceeds max safe Z ({max_safe_z})"
            )
    
        # ----------------------------------------------------------
        # 3. Clamp speed to allowed range
        # ----------------------------------------------------------
        if speed < 0 or speed > 125:
            raise ValueError(f"Z speed must be between 0 and 125 mm/sec (got {speed})")
    
        # ----------------------------------------------------------
        # 4. Execute the movement
        # ----------------------------------------------------------
        parameters = {"Z Position": position, "Z Speed": speed}
        result = self.send_command("Move Z with Speed", parameters=parameters)
    
        self.current_z = float(position)
    
        # ----------------------------------------------------------
        # 5. Infer current_module from XY + Z
        # ----------------------------------------------------------
        if self.tray is not None:
            module_name_at_xy = self.tray.get_module_at_xy(
                self.current_x, self.current_y
            )
    
            if module_name_at_xy is not None:
                module = module_name_at_xy
                if self.current_z < module.z_limits["safe"]:
                    self.current_module = module_name_at_xy
                else:
                    self.current_module = None
            else:
                self.current_module = None
    
        return f"Moved Z to {position} at {speed} mm/sec. Result: {result}"








    @log_call
    def move_xy(self, x_position, y_position, module_name=None):
        """
        Move both X and Y axes safely in one operation.
        Automatically computes the necessary Z clearance based on
        the current module and the destination module at the target XY.
        """
        
        # --- Infer the destination module from target XY ---
        destination_module = self.tray.get_module_at_xy(x_position, y_position)
        
        # --- Update current_module based on current XY ---
        if self.tray is not None:
            current_module_name = self.tray.get_module_at_xy(self.current_x, self.current_y)
            self.current_module = module_name
        
        # --- Enforce Z safety before horizontal move ---
        self.ensure_z_safe(destination_module=destination_module)
        
        # --- Execute the XY move ---
        parameters = {"X Position": x_position, "Y Position": y_position}
        result = self.send_command("Move XY", parameters=parameters)
    
        # --- Update Python-side state ---
        self.current_x = float(x_position)
        self.current_y = float(y_position)
    
        return f"Moved to X={x_position}, Y={y_position}. Result: {result}"




    @log_call
    def home(self):
        # Ensure Z is at least safe before homing X/Y
        if self.current_z < self.Z_SAFE:
            print(
                f"Z below safe limit ({self.current_z:.2f} < {self.Z_SAFE:.2f}) — raising first."
            )
            self.move_z(self.Z_SAFE)

        # Move to y=0 to avoid DIM before homing move
        if self.current_y != 0:
            print("Moving Y to 0 before homing")
            self.move_y(0)

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
        slot = self.resolve_slot(module_name)

        rack = self.tray.get_module(slot)
        off_x, off_y = self.tray.get_offsets(slot)
        x_rel, y_rel = rack.get_vial_coordinates(vial_pos)
    
        x = off_x + x_rel
        y = off_y + y_rel
    
        # ----------------------------------------------------------
        # 2. Raise Z to rack-safe height before XY
        # ----------------------------------------------------------
        self.ensure_z_safe(destination_module=module_name)
    
        # ----------------------------------------------------------
        # 3. Return only (for debugging)
        # ----------------------------------------------------------
        if not send:
            return x, y
    
        # ----------------------------------------------------------
        # 4. Move XY with module-specific Z safety active
        # ----------------------------------------------------------
        self.move_xy(x, y, module_name=module_name)
    
        return x, y



    @log_call
    def go_into_vial(self, module_name: str, vial_pos: int, send=True):
        """
        Move the probe into a specific vial of a module.
        This:
            1) Raises to GLOBAL safe height
            2) Moves XY above the vial
            3) Descends to module working_min safely
        """
    
        # --- resolve rack + coordinates ---
        slot = self.resolve_slot(module_name)

        rack = self.tray.get_module(slot)
        off_x, off_y = self.tray.get_offsets(slot)
        x_rel, y_rel = rack.get_vial_coordinates(vial_pos)
    
        x_abs = off_x + x_rel
        y_abs = off_y + y_rel
        z_target = rack.z_limits["working_min"]
    
        if not send:
            return x_abs, y_abs, z_target
    
        # ----------------------------------------------------------
        # Step 1: now do the normal XY safe-move
        # (go_to_vial will apply module-specific Z safety if needed)
        # ----------------------------------------------------------
        self.go_to_vial(module_name, vial_pos, send=True)
    
        # ----------------------------------------------------------
        # Step 2: controlled descent INTO the vial
        # temporarily override global clamps
        # ----------------------------------------------------------
        try:
            self.allow_in_vial = True
            self.move_z(z_target, allow_in_vial=True, module_name=module_name)
        finally:
            self.allow_in_vial = False

        slot = self.resolve_slot(module_name)
        self.current_module = self.tray.assigned_modules[slot]["module_id"]
    
        return x_abs, y_abs, z_target

    
    def go_to_dim(self, send=True):
        """
        Move the probe above the DIM module.
    
        Safety model:
        - Before ANY horizontal move, raise to DIM-specific safe Z
          (via ensure_z_safe(destination_module="dim")).
        """
    
        module_name = "dim"
    
        # ----------------------------------------------------------
        # 1. Resolve module + coordinates
        # ----------------------------------------------------------
        slot = self.resolve_slot("dim")
        off_x, off_y = self.tray.get_offsets(slot)
    
        x = off_x
        y = off_y
    
        # ----------------------------------------------------------
        # 2. Raise Z to DIM-safe height before XY
        # ----------------------------------------------------------
        self.ensure_z_safe(destination_module=module_name)
    
        # ----------------------------------------------------------
        # 3. Return only (for debugging)
        # ----------------------------------------------------------
        if not send:
            return x, y
    
        # ----------------------------------------------------------
        # 4. Move XY with module-specific Z safety active
        # ----------------------------------------------------------
        self.move_xy(x, y, module_name=module_name)
    
        return x, y

    @log_call
    def go_into_dim(self, valve_pos="B", speed=40, send=True):
        """
        Move the probe into the DIM. DIM moved to load
    
        This:
            1) Asserts valve position
            2) Raises to GLOBAL safe height
            3) Moves XY above the DIM
            4) Descends to DIM working_min safely
        """
    
        module_name = "dim"
        dim = self.tray.get_module(module_name)
    
        slot = self.resolve_slot("dim")
        off_x, off_y = self.tray.get_offsets(slot)
        x_abs = off_x
        y_abs = off_y
        z_target = dim.z_limits["working_min"]
    
        if not send:
            return x_abs, y_abs, z_target
    
        # ----------------------------------------------------------
        # Step 0: assert valve position BEFORE motion
        # ----------------------------------------------------------
        #dim.load()
       # dim.assert_load()
    
        # ----------------------------------------------------------
        # Step 1: XY safe-move above DIM
        # ----------------------------------------------------------
        self.go_to_dim(send=True)
    
        # ----------------------------------------------------------
        # Step 2: controlled descent INTO the DIM
        # ----------------------------------------------------------
        try:
            self.allow_in_vial = True
            self.move_z(
                z_target,
                speed=50,
                allow_in_vial=True,
                module_name=module_name
            )
        finally:
            self.allow_in_vial = False
    
        slot = self.resolve_slot(module_name)
        self.current_module = self.tray.assigned_modules[slot]["module_id"]
    
        return x_abs, y_abs, z_target


    @log_call
    def leave_dim(self):
        """
        Retract the probe safely out of the DIM.
        Vertical-only move back to DIM-safe Z.
        """
    
        module_name = "dim"
        dim = self.tray.get_module(module_name)
    
        z_safe = dim.z_limits["safe"]
    
        self.move_z(
            z_safe,
            module_name=module_name
        )
    
        self.current_module = None
    
        return z_safe

    def resolve_slot(self, name):
        """
        Resolve ANY identifier to a tray slot:
        - alias ("rack2")
        - module_id ("rack_3dp")
        - slot (2)
        """
    
        # 1. direct slot
        if isinstance(name, int):
            return name
    
        # 2. alias match
        for slot, info in self.tray.assigned_modules.items():
            if info.get("alias") == name:
                return slot
    
        # 3. module_id match
        for slot, info in self.tray.assigned_modules.items():
            if info.get("module_id") == name:
                return slot
    
        raise ValueError(f"Unknown module identifier: {name}")


    def close(self):
        if self.session_socket:
            self.session_socket.close()
            self.session_socket = None
