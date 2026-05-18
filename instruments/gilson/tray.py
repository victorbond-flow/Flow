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
                        "x_offset": 156,
                        "y_offset": 9,

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

                        "x_offset": 10,
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

        # ------------------------------------------------------------------
        # Alias registry init
        # ------------------------------------------------------------------
        self.alias_map = {}

    # ======================================================================
    # Slot assignment
    # ======================================================================

    def assign_slot(self, slot: int, module, alias: str = None):
        """
        Assign a module to a physical tray slot.
    
        Parameters
        ----------
        slot : int
            Physical tray slot number.
    
        module : object
            Module instance to place in the slot.
            Must define self.module_id.
    
        alias : str, optional
            Human-friendly name (e.g. "rack2", "dim")
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
            "alias": alias if alias is not None else module_id,
            **calibration
        }
    
        # --------------------------------------------------------------
        # Register alias (NEW)
        # --------------------------------------------------------------
        if alias is not None:
            if not hasattr(self, "alias_map"):
                self.alias_map = {}
    
            if alias in self.alias_map:
                raise ValueError(f"Alias '{alias}' already exists.")
    
            self.alias_map[alias] = slot

    # ======================================================================
    # Helper methods
    # ======================================================================

    def get_module(self, name):
        slot = self.resolve_slot(name)
    
        if slot not in self.assigned_modules:
            raise ValueError(f"No module assigned to slot {slot}.")
    
        return self.assigned_modules[slot]["module"]

    def resolve_slot(self, name):

        # CRITICAL: normalize first
        name = self.normalize(name)
    
        # direct slot
        if isinstance(name, int):
            return name
    
        # alias match
        for slot, info in self.assigned_modules.items():
            if info.get("alias") == name:
                return slot
    
        # module_id match
        for slot, info in self.assigned_modules.items():
            if info.get("module_id") == name:
                return slot
    
        raise ValueError(
            f"Unknown module identifier: {name}. "
            f"Known aliases: {[info.get('alias') for info in self.assigned_modules.values()]}"
        )

    def get_module_by_id(self, module_id):

        # match alias OR module_id OR slot name
        for slot, info in self.assigned_modules.items():
            if (
                info.get("module_id") == module_id
                or info.get("alias") == module_id
            ):
                return info["module"]
    
        raise ValueError(f"No module assigned with id {module_id}")

    def get_slot_by_alias(self, alias: str):
        """
        Return tray slot from human-readable alias (e.g. 'rack2', 'dim').
        """
    
        for slot, info in self.assigned_modules.items():
            if info.get("alias") == alias:
                return slot
    
        raise ValueError(f"No module assigned with alias '{alias}'")

    def get_offsets(self, name):
        """
        Return global X/Y offsets for a slot, alias, or module_id.
        """
    
        slot = self.resolve_slot(name)
    
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
                return slot_info["module"]

        return None

    def normalize(self, name):
        """
        Converts ANY identifier into canonical string form.
        """
        if isinstance(name, int):
            return self.assigned_modules[name]["alias"]
    
        if hasattr(name, "module_id"):
            return name.module_id
    
        if hasattr(name, "__class__"):
            # fallback: try alias reverse lookup
            for slot, info in self.assigned_modules.items():
                if info["module"] == name:
                    return info["alias"]
    
        return name

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