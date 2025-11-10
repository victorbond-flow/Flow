# tray.py
"""
Tray manager for the autosampler.

Keeps track of all modules (racks, wash stations, waste, etc.) and their positions.
Automatically reads offsets from the module objects when added.
"""

from rack import Rack_209  # import any other modules as they are added


class Tray:
    """Represents the autosampler tray with multiple modules."""

    def __init__(self):
        self.modules = {}  # key = slot/position (int), value = module object
        self.module_offsets = (
            {}
        )  # key = slot/position, value = dict of offsets (x_offset, y_offset)

    def add_module(self, slot: int, module):
        """
        Add a module to the tray.

        Parameters
        ----------
        slot : int
            Slot/position on the tray (1, 2, 3,...)
        module : object
            Module object (Rack_209, etc.) which has its own offsets
        """
        self.modules[slot] = module

        # Extract offsets if available
        offsets = {}
        if hasattr(module, "rack_offset_x") and hasattr(module, "rack_offset_y"):
            offsets = {
                "x_offset": module.rack_offset_x,
                "y_offset": module.rack_offset_y,
            }
        elif hasattr(module, "offset_x") and hasattr(module, "offset_y"):
            offsets = {"x_offset": module.offset_x, "y_offset": module.offset_y}

        self.module_offsets[slot] = offsets

    def get_module(self, slot: int):
        """Return module at a given slot, or None if empty."""
        return self.modules.get(slot, None)

    def get_offsets(self, slot: int):
        """Return offsets dict for a given slot, or empty dict if unknown."""
        return self.module_offsets.get(slot, {})

    def list_slots(self):
        """Return a sorted list of slots currently in the tray."""
        return sorted(self.modules.keys())
