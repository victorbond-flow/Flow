import numpy as np
from vial import Vial
from flow_logging import FlowLogger

logger = FlowLogger()
log_call = logger.log_call

# ==========================================================================================
# rack.py
# ------------------------------------------------------------------------------------------
#
# rack.py – Gilson GX-271 / Compatible Autosampler Rack Definitions
#
# This module defines the geometry, vial objects, and safe probe movement logic
# for racks used in the autosampler. It separates generic rack geometry from
# rack-specific details and instrument control.
#
# Contains three main classes:
#
#   • Rack
#       A generic rack geometry container.
#       Stores number of rows/columns, vial spacing, offsets, and optional staggered layouts.
#       Can compute vial coordinates and indices.
#       Does NOT include instrument-specific logic or Z-safety limits.
#
#   • Rack_209
#       Concrete implementation of the Gilson 6×16 rack (code 209).
#       Creates a Rack instance with hard-coded geometry, instantiates all Vial objects,
#       defines Z-safety limits, and constructs a Rackcommands object.
#       Concrete implementation of the Gilson 6×16 rack (code 209).
#       Wraps a Rackcommands object linked to a GilsonEthernet session for probe movements.
#       Provides a simple interface to query vial coordinates and interact with the rack
#
#   • Rackcommands (imported from rack_commands.py)
#       Uses the Rack geometry + GilsonEthernet session to perform safe probe movements:
#       moving to vials, lowering into vials, and stepping through vial sequences.
# ==========================================================================================


class Rack:
    """
    Generic rack geometry class
    Does NOT contain rack-specific geometry or vial/Z information
    """

    # --------------------------------------------------------------------------------------------------------------------------------------------------------
    def __init__(
        self,
        n_cols,
        n_rows,
        vial2vial_x,
        vial2vial_y,
        staggered=False,
        offset_x=0.0,  # Default set to 0 - offsets handled by tray - defined in NB
        offset_y=0.0
    ):

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

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------
    def all_vial_numbers(self):
        """Return a list of all vial numbers in the rack"""
        return list(self.vials.keys())

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# --- Convenience wrappers for single-vial operations (MORE USEFUL LATER - HENCE, COMMENTED OUT 05/11/25--------------------------

# def fill_vial(self, vial_num, volume, substance):
# """Fill a single vial (thin wrapper)."""
# self.vials[vial_num].fill(volume, substance)

# def empty_vial(self, vial_num):
# """Empty a single vial (thin wrapper)."""
# self.vials[vial_num].empty()

# def consume_vial(self, vial_num, volume):
# """Withdraw volume from a single vial."""
# self.vials[vial_num].consume_volume(volume)

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
    Rack-specific wrapper around the generic Rack() geometry.

    This class:
    - Defines intrinsic rack geometry (relative coordinates)
    - Creates Vial objects
    - Provides vial-relative coordinate lookup
    - Stores rack-specific Z-limits
    """

    def __init__(self):
        # Generic Rack geometry (relative coords only — *no global offsets*)
        self.rack = Rack(
            n_cols=6,
            n_rows=16,
            vial2vial_x=16.54,
            vial2vial_y=17.77,
            staggered=True,
        )

        # Rack-specific Z limits
        self.z_limits = {
            "safe": 45.0,
            "max_safe": 120.0,
            "working_min": 11.0,
        }

        # Instantiate vial objects
        self.vials = {
            vial_num: Vial(
                vial_volume_max=2.0,
                vial_usedvolume_max=1.8,
                vial_height=32.0,
                vial_free_depth=2.0,
            )
            for vial_num in self.rack.rack_order.flatten()
        }

    def get_vial_coordinates(self, vial_pos):
        """
        Return coordinates relative to the rack origin.
        The Tray will add global offsets.
        """
        return self.rack.get_vial_coordinates(vial_pos)


