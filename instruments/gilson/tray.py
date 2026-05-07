# tray.py

"""
Tray manager for the autosampler.

The Tray owns:
- physical slot footprints
- valid module placements
- placement calibrations
- runtime module assignments

Users assign modules to physical tray slots.
The Tray automatically determines global offsets.

TODO
----
- Potentially move slot definitions into a config file later
"""

from instruments.gilson.rack import Rack_209, Rack_3dp
from instruments.vici.dim import DIM


class Tray:
    """
    Represents the physical autosampler deck.

    The Tray knows:
    - what physical slots exist
    - what module types are valid in each slot
    - where each valid module sits physically

    The Tray does NOT know:
    - rack internal geometry
    - vial layouts
    - vial metadata

    Those belong to the module classes themselves.
    """

    def __init__(self):

        # ------------------------------------------------------------------
        # Physical tray slot definitions
        #
        # Structure:
        #
        # slot number
        #   -> allowed module types
        #       -> placement calibration
        #
        # Placement calibration defines the global position of the module
        # when mounted in that slot.
        # ------------------------------------------------------------------

        self.slot_definitions = {

            # ==============================================================
            # SLOT 1
            # ==============================================================

            1: {

                "allowed_modules": {

                    "rack_209": {
                        "x_offset": 155.5,
                        "y_offset": 10,

                        "x_min": 145,
                        "x_max": 250,

                        "y_min": 2,
                        "y_max": 292,
                    }
                }
            },

            # ==============================================================
            # SLOT 2
            # ==============================================================

            2: {

                "allowed_modules": {

                    "rack_3dp": {
                        "x_offset": 319,
                        "y_offset": 39,

                        "x_min": 275,
                        "x_max": 370,

                        "y_min": 2,
                        "y_max": 292,
                    }
                }
            },

            # ==============================================================
            # SLOT 3 (DIM ONLY)
            # ==============================================================

            3: {

                "allowed_modules": {

                    "dim": {

                        "x_offset": 9,
                        "y_offset": 104,

                        "x_min": 0,
                        "x_max": 25,

                        "y_min": 75,
                        "y_max": 120,
                    }
                }
            }
        }

        # ------------------------------------------------------------------
        # Runtime slot occupancy
        #
        # Stores modules currently assigned to tray slots.
        # ------------------------------------------------------------------

        self.assigned_modules = {}

    # ======================================================================
    # Slot assignment
    # ======================================================================

    def assign_slot(self, slot: int, module):
        """
        Assign a module to a physical tray slot.

        Parameters
        ----------
        slot : int
            Physical tray slot number.

        module : object
            Module instance to place in the slot.
            Must define self.module_id.
        """

        # --------------------------------------------------------------
        # Ensure slot exists
        # --------------------------------------------------------------

        if slot not in self.slot_definitions:
            raise ValueError(f"Slot {slot} does not exist on this tray.")

        # --------------------------------------------------------------
        # Ensure slot is unoccupied
        # --------------------------------------------------------------

        if slot in self.assigned_modules:
            raise ValueError(f"Slot {slot} is already occupied.")

        # --------------------------------------------------------------
        # Determine module type
        # --------------------------------------------------------------

        module_id = module.module_id

        # --------------------------------------------------------------
        # Retrieve valid modules for this slot
        # --------------------------------------------------------------

        allowed_modules = self.slot_definitions[slot]["allowed_modules"]

        # --------------------------------------------------------------
        # Ensure module is valid for this slot
        # --------------------------------------------------------------

        if module_id not in allowed_modules:
            raise ValueError(
                f"Module '{module_id}' is not valid for slot {slot}."
            )

        # --------------------------------------------------------------
        # Retrieve placement calibration
        # --------------------------------------------------------------

        calibration = allowed_modules[module_id]

        # --------------------------------------------------------------
        # Register module assignment
        # --------------------------------------------------------------

        self.assigned_modules[slot] = {
            "module": module,
            "module_id": module_id,
            **calibration
        }

    # ======================================================================
    # Helper methods
    # ======================================================================

    def get_module(self, slot: int):
        """
        Return the module instance assigned to a slot.
        """

        if slot not in self.assigned_modules:
            raise ValueError(f"No module assigned to slot {slot}.")

        return self.assigned_modules[slot]["module"]

    def get_offsets(self, slot: int):
        """
        Return global X/Y offsets for a slot.
        """

        if slot not in self.assigned_modules:
            raise ValueError(f"No module assigned to slot {slot}.")

        slot_info = self.assigned_modules[slot]

        return (
            slot_info["x_offset"],
            slot_info["y_offset"]
        )

    def get_module_at_xy(self, x: float, y: float):
        """
        Determine which assigned module footprint contains the given XY.
        """

        for slot_info in self.assigned_modules.values():

            if (
                slot_info["x_min"] <= x <= slot_info["x_max"]
                and
                slot_info["y_min"] <= y <= slot_info["y_max"]
            ):
                return slot_info["module_id"]

        return None

    def list_assignments(self):
        """
        Return currently assigned modules.
        """

        return [
            {
                "slot": slot,
                "module_id": info["module_id"]
            }
            for slot, info in self.assigned_modules.items()
        ]