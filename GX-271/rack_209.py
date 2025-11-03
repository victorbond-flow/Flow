import numpy as np
from gilson_ethernet2 import GilsonSession
# from loguru import logger  # Optional logging

##########################################################################################################################
# rack_209.py    Note - the number in the file name reflects the code associated with the specific rack on Gilsons website
# -------------------------------------------------------------------------------------------
# Specific implementation for the 6×16 rack used on the Gilson GX-271 autosampler.
#
# Defines the geometry, spacing, and coordinates for this particular rack.
# The class can be imported directly to provide vial positions without 
# needing to specify any geometry in the control notebook.
#
# Classes defined:
#   - Rack : Hardcoded 6×16 rack with coordinate mapping
#   - Rackcommands   : Interface between the rack and Gilson session
#   - Vial           : Represents a single vial
#   - SetupVolumes   : Helper class for flow system volume calculations
#
# NOTE: For other rack types, clone this file and update the hardcoded geometry.
##########################################################################################################################


class Rack:
    """
    Generic rack geometry class
    Does NOT contain rack-specific geometry or vial/Z information
    """

# --------------------------------------------------------------------------------------------------------------------------------------------------------
# 1. INITIAL SETUP + STRUCTURE
# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 n_cols,
                 n_rows,
                 offset_x,
                 offset_y,
                 vial2vial_x,
                 vial2vial_y,
                 staggered=False):
        
        self.n_cols = n_cols
        self.n_rows = n_rows
        self.array_dimensions = (self.n_cols, self.n_rows)

        self.offset_x = offset_x
        self.offset_y = offset_y

        self.vial2vial_x = vial2vial_x
        self.vial2vial_y = vial2vial_y

        self.staggered = staggered

        # Build rack order
        self.rack_order = self.generate_vial_order()


# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def generate_vial_order(self):
        """Generate vial numbers (column-major order, default Gilson behaviour)."""
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
        """Return (x, y) coordinates in mm for the given vial position."""
    
        row, col = self.get_vial_indices(vial_position)
    
        x = self.offset_x + col * self.vial2vial_x
        y = self.offset_y + row * self.vial2vial_y
    
        # Optional: staggered pattern
        if self.staggered and (col % 2 == 1):
            y += self.vial2vial_y / 2
    
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
# Rack_209
# -------------------------------------------------------------------------------------------
# rack-specific configuration for the GX-271 6×16 rack (Gilson rack code 209)
#############################################################################################

class Rack_209
    """
    Rack-specific wrapper class following the architecture used by Anna.

    This class:
    - Instantiates the generic Rack() (for now still the hardcoded version)
    - Creates all Vial objects
    - Creates a Rackcommands object linked to a GilsonSession
    - Allows uniform usage across different racks (Rack_4_16, Rack_209, etc.)
    """
    def __init__(self, gilson_session,
                 rack_position=1,
                 rack_offset_x=92,
                 rack_offset_y=0,
                 rack_home_x=3.8,
                 rack_home_y=2.3):

        #Pass geometry into Rack()
        self.rack = Rack(
            n_cols=6,
            n_rows=16,
            offset_x=35.5,
            offset_y=7.2,
            vial2vial_x=16.54,
            vial2vial_y=17.77,
            staggered=True
        )

        #Rack-specific Z limits
        self.z_limits = {
            "safe": 45.0,
            "max_safe": 120.0,
            "working_min": 11.0,
        }

        #Instantiate vial objects here now
        self.vials = {
            vial_num: Vial(
                vial_volume_max=2.0,
                vial_usedvolume_max=1.8,
                vial_height=32.0,
                vial_free_depth=2.0
            )
            for vial_num in self.rack.rack_order.flatten()
        }

        #Create commands object
        self.commands = Rackcommands(
            gilson_session,
            self.rack,
            rack_position=rack_position,
            rack_offset_x=rack_offset_x,
            rack_offset_y=rack_offset_y,
            rack_home_x=rack_home_x,
            rack_home_y=rack_home_y
        )


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

    def go_to_vial(self, vial_pos, send=True):
        """Move the Gilson probe to the vial at vial_pos."""

        # Get base geometry from rack
        x, y = self.rack.get_vial_coordinates(vial_pos)

        # Apply rack stacking offsets
        x += (self.rack_position - 1) * self.rack_offset_x
        y += (self.rack_position - 1) * self.rack_offset_y

        if not send:
            return x, y

        # Safety: always raise Z before XY movement
        if self.gilson.current_z < self.z_limits["safe"]:
            print(f"Raising to Z_SAFE ({self.z_limits['safe']} mm) before XY move...")
            self.gilson.move_z(self.z_limits["safe"])

        print(f"Moving to vial {vial_pos} at ({x:.2f}, {y:.2f}) mm")
        self.gilson.move_xy(x, y)

        return x, y

    # --------------------------------------------------------------------------------------------

    def move_into_vial(self):
        """Lower probe into vial to minimum safe working depth."""

        target_z = self.z_limits["working_min"]
        print(f"Lowering probe to working minimum Z = {target_z} mm")
        self.gilson.move_z(target_z, allow_in_vial=True)

    # --------------------------------------------------------------------------------------------

    def move_sequence(self, vials):
        """Move through a sequence of vials in order."""
        for v in vials:
            self.go_to_vial(v)

    
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
