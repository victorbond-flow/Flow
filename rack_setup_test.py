"""
rack_setup_test.py
------------------
Define and test vial rack geometry for your Gilson GX271 autosampler.

This script focuses on validating X/Y positioning logic (rack layout,
vial numbering, offsets, spacing, etc.) before integration with
the GilsonSession communication class.

Run it directly or import into a Jupyter Notebook to print and inspect
rack coordinates for given vial numbers.
"""

# ============================================================
# Imports
# ============================================================

import numpy as np          # For defining vial layout arrays
import time                 # For timing/debug prints
import sys                  # For potential exit or exception handling
#from loguru import logger   # Optional but nice logging output
from rack import Rack, Rackcommands  # Uses your existing rack.py definitions


# ============================================================
# Logging configuration
# ============================================================

# You can comment this out if you don't want console logs.
#logger.remove()
#logger.add(sys.stdout, colorize=True,
            #format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


# ============================================================
# Rack Definition and Setup
# ============================================================

def get_rack_setup():
    """
    Define one or more racks used by the autosampler deck.

    These geometry values are placeholders based on the GX241 and
    should be updated for your GX271 once you've measured the real
    offsets and spacing.
    """

    # -- Physical rack geometry (mm) -- Still needs set up specifically for my rack
    array_dimensions = [4, 12]        # [columns, rows] - adjust for your rack
    offset_x = 8.7                    # mm from system home (X)
    offset_y = 40.0                   # mm from system home (Y)
    vial2vial_x = 2.11 + 15.6         # spacing between vial centers (X, mm)
    vial2vial_y = 2.72 + 15.6 + 0.35  # spacing between vial centers (Y, mm)
    groundlevel_height = 65           # surface or top-of-rack level (mm)

    #logger.info("Defining rack geometry and array layout...")

    # -- Rack object creation --
    rack = Rack(
        array_dimensions=array_dimensions,
        offset_x=offset_x,
        offset_y=offset_y,
        vial2vial_x=vial2vial_x,
        vial2vial_y=vial2vial_y,
        groundlevel_height=groundlevel_height
    )

    # -- Vial numbering layout --
    # This layout visually represents the rack. Adjust once you know the
    # physical orientation (e.g., whether vial 1 starts top-left or bottom-left).
    array_order = np.array([
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12],
        [13, 14, 15, 16],
        [17, 18, 19, 20],
        [21, 22, 23, 24],
        [25, 26, 27, 28],
        [29, 30, 31, 32],
        [33, 34, 35, 36],
        [37, 38, 39, 40],
        [41, 42, 43, 44],
        [45, 46, 47, 48]
    ])

    # -- Translate vial indices into XY coordinates --
    rack_commands = Rackcommands(rack, array_order, rack_position=1)

    #logger.info("Rack and command mapping created successfully.")
    return rack, rack_commands


# ============================================================
# Rack Testing / Coordinate Verification
# ============================================================

def test_rack_positions():
    """
    Prints X/Y coordinates for selected vial numbers.
    Use this to confirm correct mapping before any real movement.
    """

    logger.info("Testing rack coordinate mapping...")
    rack, rack_commands = get_rack_setup()

    # Vial numbers to test (choose any)
    test_vials = [1, 6, 12, 24, 36, 48]
    logger.info(f"Testing vials: {test_vials}")

    # Loop through and print each result
    for vial in test_vials:
        coords = rack_commands.get_xy_command(vial)
        logger.info(f"Vial {vial}: {coords}")

        # Short pause for readability
        time.sleep(0.2)

    logger.success("Rack coordinate test completed successfully.")


# ============================================================
# Main execution
# ============================================================

if __name__ == "__main__":
    logger.info("Starting rack setup test environment...\n")
    test_rack_positions()

