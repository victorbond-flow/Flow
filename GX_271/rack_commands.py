from flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

#############################################################################################
# Rackcommands
# -------------------------------------------------------------------------------------------
# Connects a Gilson autosampler session (GilsonEthernet) to a specific Rack instance
# and provides safe, coordinate-based probe movement commands.
#
# Key responsibilities:
#   - Translate vial numbers to XY coordinates based on rack geometry and offsets
#   - Ensure Z-axis safety when moving between vials or lowering into vials
#   - Provide wrappers for common actions like go_to_vial() and move_into_vial()
#   - Support multi-rack layouts via rack_position and stacking offsets
#   - Maintain separation between geometry, rack-specific limits, and instrument commands
#
# Relationships:
#   - Relies on Rack to supply vial coordinates and geometry
#   - Relies on GilsonEthernet to execute actual probe movements
#   - GilsonEthernet.move_into_vial() simply routes the call to this class
#
# Notes:
#   - Z-safety limits are taken from the rack if defined, otherwise fall back to
#     GilsonEthernet defaults
#   - move_sequence() is a scaffold for iterating through multiple vials in order
#############################################################################################


class Rackcommands:
    """Connects a Gilson session to a Rack and handles vial movements."""

    def __init__(self, gilson_session, rack,
                 rack_position=1, rack_offset_x=92, rack_offset_y=0, rack_home_x=3.8, rack_home_y=2.3):
        self.gilson = gilson_session
        self.rack = rack

        # Position of this rack in a multi-rack deck layout
        self.rack_position = rack_position
        self.rack_offset_x = rack_offset_x
        self.rack_offset_y = rack_offset_y

        # Home positions (rack-origin reference)
        self.rack_home_x = rack_home_x
        self.rack_home_y = rack_home_y

        # NEW - store geometry name for debugging
        self.rack_name = getattr(rack, "name", f"Rack-{rack_position}")

        # Use rack-defined Z safety limits if they exist
        if hasattr(rack, "z_limits"):
            self.z_limits = rack.z_limits
        else:
            # fallback (just use Gilson defaults)
            self.z_limits = {
                "safe": self.gilson.Z_SAFE,
                "max_safe": self.gilson.Z_MAX_SAFE,
                "working_min": self.gilson.Z_WORKING_MIN,
            }

    # --------------------------------------------------------------------------------------------

    @log_call
    def go_to_vial(self, vial_pos, send=True):
        """Move the Gilson probe to the vial at vial_pos, respecting rack-specific Z limits.
        The 'send=False' option returns the calculated coordinates without moving,
        which is useful for debugging or pre-checking vial positions.
        
        """
    
        # Get base XY coordinates from the rack
        x, y = self.rack.get_vial_coordinates(vial_pos)
    
        # Apply rack stacking offsets
        x += (self.rack_position - 1) * self.rack_offset_x
        y += (self.rack_position - 1) * self.rack_offset_y
    
        # -----------------------------
        # RACK-SPECIFIC Z SAFETY CHECK
        # -----------------------------
        safe_z = self.z_limits.get("safe", self.gilson.Z_SAFE)
        if self.gilson.current_z < safe_z:
            print(f"Raising to rack-safe Z ({safe_z} mm) before XY move...")
            self.gilson.move_z(safe_z)
    
        if not send:
            return x, y
    
        # Move XY
        print(f"Moving to vial {vial_pos} at ({x:.2f}, {y:.2f}) mm")
        self.gilson.move_xy(x, y, rack_num=self.rack_position)

    
        return x, y


    # --------------------------------------------------------------------------------------------
    @log_call
    def move_into_vial(self):
        """Lower probe into vial to the rack-specific minimum safe working depth.
        Relationship to GilsonEthernet:
        GilsonEthernet.move_into_vial() only routes the call to the correct rack.
        THIS method is responsible for deciding how far into the vial to go.
        """
    
        # Use the rack's working_min, fallback to GilsonEthernet default if not set
        target_z = self.z_limits.get("working_min", self.gilson.Z_WORKING_MIN)
        print(f"Lowering probe into vial to Z = {target_z} mm (rack-specific working min)")
        
        # Allow moving below Z_SAFE since we are entering the vial
        self.gilson.move_z(target_z, allow_in_vial=True)


    # --------------------------------------------------------------------------------------------
    
    def move_sequence(self, vials):
        """Move through a sequence of vials in order. Note - scaffold class, may be useful later"""
        for v in vials:
            self.go_to_vial(v)