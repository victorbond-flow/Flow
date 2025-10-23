import numpy as np
from gilson_ethernet2 import GilsonSession
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
        (n_columns, n_rows) — number of vials in each dimension.                         #NOTE - THIS NEEDS UPDATED!!!
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

# --------------------------------------------------------------------------------------------------------------------------------------------------------
# 1. INITIAL SETUP + STRUCTURE
# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def __init__(self, array_dimensions, offset_x, offset_y,
             vial2vial_x, vial2vial_y, groundlevel_height,
             staggered=True,
             vial_volume_max=None, vial_usedvolume_max=None,
             vial_height=None, vial_free_depth=None):

        self.n_cols, self.n_rows = array_dimensions
        self.array_dimensions = array_dimensions
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.vial2vial_x = vial2vial_x
        self.vial2vial_y = vial2vial_y
        self.groundlevel_height = groundlevel_height
        self.staggered = staggered
        self.rack_order = self.generate_vial_order()
        self.vials = {vial_num: Vial(vial_volume_max, vial_usedvolume_max, vial_height, vial_free_depth)
                      for vial_num in self.rack_order.flatten()}

# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def generate_vial_order(self):
        """Create an array that defines the vial numbering pattern.

        Generate vial numbers in regular column-major order (top-to-bottom, left-to-right)."""
        order = np.zeros((self.n_rows, self.n_cols), dtype=int)
        vial_number = 1
        for c in range(self.n_cols):
            for r in range(self.n_rows):
                order[r, c] = vial_number
                vial_number += 1
        return order
        
#---------------------------------------------------------------------------------------------------------------------------------------------------------
    def all_vial_numbers(self):
        """Return a list of all vial numbers in the rack"""
        return list(self.vials.keys())

# --------------------------------------------------------------------------------------------------------------------------------------------------------
# 2. GEOMETRY + POSITION METHODS
# --------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def get_vial_indices(self, vial_position):
        """Return (row, col) indices for a given vial number."""
        indices = np.where(self.rack_order == vial_position)
        if len(indices[0]) == 0:
            raise ValueError(f"No vial with position {vial_position}")
        return indices[0][0], indices[1][0]

# --------------------------------------------------------------------------------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------------
# 3. NEW - VIAL MANAGEMENT METHODS
# ------------------------------------------------------------------------------------
    def fill_vial(self, vials, volume, substance):
        """Record that specified vials have been filled manually"""
        if isinstance(vials, int):
            vials = [vials]

        # Verify that all vials exist first
        for v in vials:
            if v not in self.vials:
                raise ValueError(f"Vial {v} does not exist in this rack.")

        # Check that the contents are consistent (all or nothing - subject to change)
        for v in vials:
            vial = self.vials[v]
            if vial.contents is not None and vial.contents != substance:
                raise ValueError(f"Vial {v} contains {vial.contents}. Empty before filling with {substance}.")

        # Proceed to fill all
        for v in vials:
            self.vials[v].fill(volume, substance)

#-----------------------------------------------------------------------------------------------------------------------------
    def empty_vial(self, vials):
        """Empty one or more vials."""
        if isinstance(vials, int):
            vials = [vials]
        for v in vials:
            if v not in self.vials:
                raise ValueError(f"Vial {v} does not exist in this rack.")
            self.vials[v].empty()
            
#--------------------------------------------------------------------------------------------------------------------------------
    def get_vial_status(self, vials=None):
        """Return readable status for specified vials or all if none specified"""
        if vials is None:
            vials = self.all_vial_numbers()
        elif isinstance(vials, int):
            vials = [vials]

        return {v: self.vials[v].get_vial_status() for v in vials}
    

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

#---------------------------------------------------------------------------------------------------------------------------------------------------------
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

        if not send:
            return x, y

        # ---- NEW SAFETY STEP: Lift Z to safe Z before XY move ---
        if self.gilson.current_z < self.gilson.Z_SAFE:
            print(f"Raising to Z_SAFE ({self.gilson.Z_SAFE} mm) before XY move...")
            self.gilson.move_z(self.gilson.Z_SAFE)

        # --- Then move in XY plane safely ---
        print(f"Moving to vial {vial_pos} at ({x:.2f}, {y:.2f}) mm")
        self.gilson.move_xy(x, y)  

        return x, y

#---------------------------------------------------------------------------------------------------------------------------------------------------------
    # The method below is a scaffold to build on later - will be useful for automating a sequence of movements between vials
    def move_sequence(self, vials):
        for v in vials:
            self.go_to_vial(v)


#############################################################################################
# Vial Class
#############################################################################################

class Vial:
    """Representation for a Vial within the flow setup."""
    def __init__(self, vial_volume_max, vial_usedvolume_max, vial_height, vial_free_depth):
        self.vial_volume_max = vial_volume_max          # volume in mL
        self.vial_usedvolume_max = vial_usedvolume_max  # volume in mL
        self.vial_height = vial_height                  # height in mm
        self.vial_free_depth = vial_free_depth          # depth in mm
        self.sum_liquid_level = 0
        self.current_volume = 0.0                       # current volume in mL
        self.contents = None                            # substance string (e.g., "0.5mM Reagent A")
        self.min_usable_fraction = 0.10                 
        self.vial_min_usable_volume = self.vial_volume_max * self.min_usable_fraction               # Defines a "functional empty" state, 10% of max volume

# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def fill(self, volume, substance):
        """ Logs that the vial has been filled manually.

        Parameters
        ----------
        volume : float --- volume (mL) to record
        substance : str --- Name of substance being added
        """

        if self.contents is not None and self.contents != substance:
            raise ValueError(f"Vial contains {self.contents}. Empty before filling with {substance}.")

        if volume > self.vial_volume_max:
            print(f"Volume {volume} exceeds vial max ({self.vial_volume_max}). Setting volume to max...")
            volume = self.vial_volume_max

        self.current_volume = volume
        self.contents = substance
        print(f"Vial filled with {volume} mL of {substance}.")

# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def empty(self):
        """Empty the vial and reset contents"""
        self.current_volume = 0.0
        self.contents = None
        print("Vial emptied - clean or replace before refill")

# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def consume_volume(self, volume):
        """Reduce the volume after withdrawal (used by Pump class)"""
        if self.current_volume == 0:
            raise ValueError("Vial is empty - cannot withdraw.")
            
        if self.current_volume - volume < self.vial_min_usable_volume:
            raise ValueError(f"Withdrawal of {volume} mL would drop the volume below safe working limit"
                             f"({self.vial_min_usable_volume:.2f} mL). Refill or replace vial.")

        self.current_volume -= volume
        print(f"Withdrawn {volume} mL. Remaining: {self.current_volume:.2f} mL of {self.contents}.")
        
# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def is_usable(self):
        """Return True if vial still has sufficient volume for use"""
        return self.current_volume > self.vial_min_usable_volume

# -------------------------------------------------------------------------------------------------------------------------------------------------------   
    def get_vial_status(self):
        if self.contents:
            return f"Vial contains {self.current_volume} mL of {self.contents}."
        else:
            return "Vial is empty."

    
###############################################################################################
# SetupVolumes Class
###############################################################################################

class SetupVolumes:
    """
    Represents the physical volumes (in mL) of different parts of the flow setup.
    These are used to calculate how long it takes to rinse, fill, or reach steady state
    based on given flow rates.

    Essentially: this class turns *flow rates* and *setup geometry* into *timing data*.
    """
    def __init__(self,
                 volume_valve_to_needle,
                 volume_reactor_to_valve,
                 volume_before_reactor,
                 volume_reactor,
                 volume_only_pump_a,
                 volume_only_pump_b,
                 volume_pump_a_and_pump_b,
                 excess=1.5):
        self.volume_valve_to_needle = volume_valve_to_needle
        self.volume_reactor_to_valve = volume_reactor_to_valve
        self.volume_before_reactor = volume_before_reactor
        self.volume_reactor = volume_reactor
        self.excess = excess
        self.volume_only_pump_a = volume_only_pump_a
        self.volume_only_pump_b = volume_only_pump_b
        self.volume_pump_a_and_pump_b = volume_pump_a_and_pump_b

# This calculates the time in seconds to fill the volume between valve and needs, given a total flowrate.
    def get_time_fill_needle(self, flowrate_a, flowrate_b, flowrate_sum):
        """Return time in sec to fill the needle at a certain flow rate."""
        duration = ((self.volume_valve_to_needle / flowrate_sum) * self.excess) * 60
        return duration
        
# This calculates the the time it takes to reach steady state after switching feeds
    def get_time_stady_state_rinsing(self, flowrate_a, flowrate_b, flowrate_sum, stady_state_rinsing_factor):
        """Return time in sec it takes to reach steady state."""
        duration = ((((self.volume_reactor * stady_state_rinsing_factor) / flowrate_b)
                     + (self.volume_pump_a_and_pump_b / flowrate_sum)) * self.excess) * 60
        return duration

# This calculates the time it takes to fill both the volume before the reactor, and the reactor itself
    def get_time_fill_reactor(self, flowrate_a, flowrate_b, flowrate_sum):
        """Return time in sec to fill the reactor."""
        duration = (((self.volume_before_reactor + self.volume_reactor) / flowrate_b)
                    * self.excess) * 60
        return duration
