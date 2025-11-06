import numpy as np
from vial import Vial
from rack_commands import Rackcommands
from flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

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
# --- Convenience wrappers for single-vial operations (MORE USEFUL LATER - HENCE, COMMENTED OUT 05/11/25--------------------------
    
    #def fill_vial(self, vial_num, volume, substance):
        #"""Fill a single vial (thin wrapper)."""
        #self.vials[vial_num].fill(volume, substance)

    #def empty_vial(self, vial_num):
        #"""Empty a single vial (thin wrapper)."""
       # self.vials[vial_num].empty()

   # def consume_vial(self, vial_num, volume):
       # """Withdraw volume from a single vial."""
        #self.vials[vial_num].consume_volume(volume)

   # def get_vial_status(self, vial_num):
      #  """Return status of a single vial."""
       # return self.vials[vial_num].get_vial_status()




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

    def get_vial_coordinates(self, vial_pos):
        return self.rack.get_vial_coordinates(vial_pos)



    