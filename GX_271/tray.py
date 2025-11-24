# tray.py
"""
Tray manager for the autosampler.

Keeps track of all modules (racks, wash stations, waste, etc.) and their positions.
Automatically reads offsets from the module objects when added.
"""

from rack import Rack_209  # import any other modules as they are added


class Tray:
    """
    Represents the autosampler tray layout.

    Each module has:
        - slot number (physical tray position)
        - name (human-friendly key)
        - module object (Rack_209, WashStation, etc.)
        - absolute X/Y offsets of that slot
    """

    def __init__(self):
        # slot -> (name, module, x_offset, y_offset)
        self.slots = {}
        # name -> slot
        self.name_to_slot = {}

    def add_module(self, slot: int, name: str, module, x_offset: float, y_offset: float):
        if name in self.name_to_slot:
            raise ValueError(f"Module name '{name}' already exists on tray!")

        self.slots[slot] = {
            "name": name,
            "module": module,
            "x_offset": x_offset,
            "y_offset": y_offset
        }
        self.name_to_slot[name] = slot

    def get_module(self, name: str):
        slot = self.name_to_slot[name]
        return self.slots[slot]["module"]

    def get_offsets(self, name: str):
        slot = self.name_to_slot[name]
        d = self.slots[slot]
        return d["x_offset"], d["y_offset"]

    def get_slot(self, name: str):
        return self.name_to_slot[name]

    def list_modules(self):
        return list(self.name_to_slot.keys())


