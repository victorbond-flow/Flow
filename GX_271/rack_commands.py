from flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

#############################################################################################
# Rackcommands
# -------------------------------------------------------------------------------------------
# Generates coordinate-based motion commands for the autosampler.
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
        """Move the Gilson probe to the vial at vial_pos, respecting rack-specific Z limits."""
    
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
        """Lower probe into vial to the rack-specific minimum safe working depth."""
    
        # Use the rack's working_min, fallback to GilsonSession default if not set
        target_z = self.z_limits.get("working_min", self.gilson.Z_WORKING_MIN)
        print(f"Lowering probe into vial to Z = {target_z} mm (rack-specific working min)")
        
        # Allow moving below Z_SAFE since we are entering the vial
        self.gilson.move_z(target_z, allow_in_vial=True)


    # --------------------------------------------------------------------------------------------
    
    def move_sequence(self, vials):
        """Move through a sequence of vials in order. Note - scaffold class, may be useful later"""
        for v in vials:
            self.go_to_vial(v)