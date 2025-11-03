import numpy as np
from gilson_ethernet2 import GilsonSession
# from loguru import logger  # Optional logging

# ==========================================================================================
# rack.py
# ------------------------------------------------------------------------------------------
# Provides the rack geometry, vial objects, and autosampler movement logic used to control
# the Gilson GX-271 (or compatible) autosampler.
#
# Contains three main classes:
#
#   • Rack
#       Generic rack geometry (rows, columns, spacing, staggered layout).
#       Computes vial coordinates but includes no instrument-specific logic.
#
#   • Rack_209
#       Concrete implementation of the Gilson 6×16 rack (code 209).
#       Creates a Rack instance with hard-coded geometry, instantiates all Vial objects,
#       defines Z-safety limits, and constructs a Rackcommands object.
#
#   • Rackcommands
#       Uses the Rack geometry + GilsonSession to perform safe probe movements:
#       moving to vials, lowering into vials, and stepping through vial sequences.
#
# Structure keeps geometry, configuration, and movement control cleanly separated and easy
# to modify for new racks or autosampler setups.
# ==========================================================================================



class Rack:
    """
    Generic rack geometry class
    Does NOT contain rack-specific geometry or vial/Z information
    """
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

#---------------------------------------------------------------------------------------------------------------------------------------------------------
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
#---------------------------------------------------------------------------------------------------------------------------------------------------------
# --- Convenience wrappers for single-vial operations ---
    def fill_vial(self, vial_num, volume, substance):
        """Fill a single vial (thin wrapper)."""
        self.vials[vial_num].fill(volume, substance)

    def empty_vial(self, vial_num):
        """Empty a single vial (thin wrapper)."""
        self.vials[vial_num].empty()

    def consume_vial(self, vial_num, volume):
        """Withdraw volume from a single vial."""
        self.vials[vial_num].consume_volume(volume)

    def get_vial_status(self, vial_num):
        """Return status of a single vial."""
        return self.vials[vial_num].get_vial_status()




#############################################################################################
# Rack_209
# -------------------------------------------------------------------------------------------
# rack-specific configuration for the GX-271 6×16 rack (Gilson rack code 209)
#############################################################################################

class Rack_209:
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
        """Move through a sequence of vials in order. Note - scaffold class, may be useful later"""
        for v in vials:
            self.go_to_vial(v)

    