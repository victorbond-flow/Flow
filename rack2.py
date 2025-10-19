import numpy as np
# from loguru import logger  # Optional logging

#############################################################################################
# rack2.py
# -------------------------------------------------------------------------------------------
# Defines classes to represent the physical layout of a Gilson rack and related operations.
# This version supports:
#   • Non-rectangular (staggered) vial layouts
#   • Serpentine (S-shaped) numbering pattern
#   • Modular rack + command structure for future automation
#############################################################################################

class Rack:
    """Representation of a physical vial rack within the flow setup.

    Handles layout geometry, vial indexing, and coordinate generation.

    Parameters
    ----------
    array_dimensions : tuple(int, int)
        (n_columns, n_rows) — number of vials in each dimension.
        e.g. (4, 16) for your 4-column × 16-row rack.
    offset_x, offset_y : float
        Base offset (mm) from the Gilson home position to vial (1,1).
    vial2vial_x, vial2vial_y : float
        Spacing between adjacent vials in mm.
    groundlevel_height : float
        Z-height reference for the deck surface (mm).
    staggered : bool, optional
        If True, every second column is offset in Y by ½ vial2vial_y
        (the “cans of beans” packing).
    """

    def __init__(self, array_dimensions, offset_x, offset_y,
                 vial2vial_x, vial2vial_y, groundlevel_height,
                 staggered=True):

        self.n_cols, self.n_rows = array_dimensions
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.vial2vial_x = vial2vial_x
        self.vial2vial_y = vial2vial_y
        self.groundlevel_height = groundlevel_height
        self.staggered = staggered

        # Build the vial numbering order automatically.
        # Column-based serpentine (S-shape) pattern.
        self.rack_order = self._generate_serpentine_order()

    # ---------------------------------------------------------------------------------------
    def _generate_serpentine_order(self):
        """Create an array that defines the vial numbering pattern.

        For a 4×16 rack, this returns an array where:
          - Col 0: 1–16 (top→bottom)
          - Col 1: 17–32 (bottom→top)
          - Col 2: 33–48 (top→bottom)
          - Col 3: 49–64 (bottom→top)
        """
        rack_order = np.zeros((self.n_rows, self.n_cols), dtype=int)
        vial_number = 1
        for c in range(self.n_cols):
            col_range = np.arange(vial_number, vial_number + self.n_rows)
            if c % 2 == 1:
                col_range = col_range[::-1]  # Reverse every second column
            rack_order[:, c] = col_range
            vial_number += self.n_rows
        return rack_order

    # ---------------------------------------------------------------------------------------
    def get_vial_indices(self, vial_position):
        """Return (row, col) indices for a given vial number."""
        indices = np.where(self.rack_order == vial_position)
        if len(indices[0]) == 0:
            raise ValueError(f"No vial with position {vial_position}")
        return indices[0][0], indices[1][0]

    # ---------------------------------------------------------------------------------------
   def get_vial_coordinates(self, vial_position):
    """Return (x, y) coordinates in mm for the given vial position.
    
    Assumes this rack always has a staggered pattern:
    every second column is shifted down by half the Y-spacing.
    """
    # Find which row and column this vial is in
    row, col = self.get_vial_indices(vial_position)

    # Compute X coordinate — each column is vial2vial_x apart
    x = self.offset_x + col * self.vial2vial_x

    # Compute Y coordinate — each row is vial2vial_y apart,
    # but odd columns (1, 3, 5...) are shifted downward.
    y = self.offset_y + row * self.vial2vial_y + (self.vial2vial_y / 2 if col % 2 == 1 else 0)

    return x, y



#############################################################################################
# Rackcommands
# -------------------------------------------------------------------------------------------
# Generates coordinate-based motion commands for the autosampler.
#############################################################################################

class Rackcommands:
    """Connects a Gilson session to a Rack and handles vial movements."""

    def __init__(self, gilson_session, rack,
                 rack_position=1, rack_offset_x=92, rack_offset_y=0):
        self.gilson = gilson_session
        self.rack = rack
        self.rack_position = rack_position
        self.rack_offset_x = rack_offset_x
        self.rack_offset_y = rack_offset_y

    def go_to_vial(self, vial_pos, send=True):
        """Move to a given vial (or return the Gilson command string).

        Parameters
        ----------
        vial_pos : int
            The vial number you want to go to.
        send : bool
            If True → send the command to the Gilson.
            If False → just return the "X.../Y..." command string.
        """
        # Get the (x, y) from the Rack object
        x, y = self.rack.get_vial_coordinates(vial_pos)

        # Apply rack-level offsets if needed (e.g., multiple racks)
        x += (self.rack_position - 1) * self.rack_offset_x
        y += (self.rack_position - 1) * self.rack_offset_y

        # Format the Gilson command
        command = f"X{x:.2f}/Y{y:.2f}"

        if send:
            print(f"Moving to vial {vial_pos} at ({x:.2f}, {y:.2f}) mm")
            self.gilson.send_command(command)  # or .move_to(x, y), depending on your driver
        else:
            return command



#############################################################################################
# Vial + SetupVolumes (unchanged from rack.py)
# -------------------------------------------------------------------------------------------
#############################################################################################

class Vial:
    """Representation for a Vial within the flow setup."""
    def __init__(self, vial_volume_max, vial_usedvolume_max, vial_height, vial_free_depth):
        self.vial_volume_max = vial_volume_max          # volume in mL
        self.vial_usedvolume_max = vial_usedvolume_max  # volume in mL
        self.vial_height = vial_height                  # height in mm
        self.vial_free_depth = vial_free_depth          # depth in mm
        self.sum_liquid_level = 0


class SetupVolumes:
    """Representation for all volumes within the flow setup to calculate rinsing times."""
    def __init__(self, volume_valve_to_needle, volume_reactor_to_valve, volume_before_reactor,
                 volume_reactor, volume_only_pump_a, volume_only_pump_b, volume_pump_a_and_pump_b,
                 excess=1.5):
        self.volume_valve_to_needle = volume_valve_to_needle
        self.volume_reactor_to_valve = volume_reactor_to_valve
        self.volume_before_reactor = volume_before_reactor
        self.volume_reactor = volume_reactor
        self.excess = excess
        self.volume_only_pump_a = volume_only_pump_a
        self.volume_only_pump_b = volume_only_pump_b
        self.volume_pump_a_and_pump_b = volume_pump_a_and_pump_b

    def get_time_fill_needle(self, flowrate_a, flowrate_b, flowrate_sum):
        """Return time in sec to fill the needle at a certain flow rate."""
        duration = ((self.volume_valve_to_needle / flowrate_sum) * self.excess) * 60
        return duration

    def get_time_stady_state_rinsing(self, flowrate_a, flowrate_b, flowrate_sum, stady_state_rinsing_factor):
        """Return time in sec it takes to reach steady state."""
        duration = ((((self.volume_reactor * stady_state_rinsing_factor) / flowrate_b)
                     + (self.volume_pump_a_and_pump_b / flowrate_sum)) * self.excess) * 60
        return duration

    def get_time_fill_reactor(self, flowrate_a, flowrate_b, flowrate_sum):
        """Return time in sec to fill the reactor."""
        duration = (((self.volume_before_reactor + self.volume_reactor) / flowrate_b)
                    * self.excess) * 60
        return duration
