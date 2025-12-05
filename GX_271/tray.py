# tray.py
"""
Tray manager for the autosampler.

Keeps track of all modules (racks, wash stations, waste, etc.) and their positions.
Automatically reads offsets from the module objects when added.
"""

from GX_271.rack import Rack_209  # import any other modules as they are added


class Tray:
    """
    Represents the autosampler tray layout.

    The Tray is the ONLY object that knows where modules
    (racks, wash stations, etc.) physically sit on the deck.

    It assigns:
    - slot number (physical location on the deck)
    - a human-friendly name ("rack1", "wash", etc.)
    - a module instance (Rack_209, WashStation, ...)
    - global X/Y offsets for that module
    """

    def __init__(self):
        # slot → { name, module, x_offset, y_offset }
        self.slots = {}

        # name → slot
        self.name_to_slot = {}

    def add_module(self, slot: int, name: str, module, x_offset: float, y_offset: float):
        """
        Add a module (e.g., rack or wash station) to a physical tray slot.

        Parameters
        ----------
        slot : int
            Physical tray position to occupy.
        name : str
            Human-readable identifier used to reference this module.
        module : object
            The module instance (provides relative geometry).
        x_offset, y_offset : float
            Global coordinates (mm) of the module’s origin on the tray.
        """
        
        if name in self.name_to_slot:
            raise ValueError(f"Module name '{name}' already exists on the tray.")

        if slot in self.slots:
            raise ValueError(f"Slot {slot} already occupied by '{self.slots[slot]['name']}'.")

        self.slots[slot] = {
            "name": name,
            "module": module,
            "x_offset": float(x_offset),
            "y_offset": float(y_offset),
        }
        self.name_to_slot[name] = slot

    def get_module(self, name: str):
        """Return the module instance for this tray name."""
        slot = self.name_to_slot[name]
        return self.slots[slot]["module"]

    def get_offsets(self, name: str):
        """Return global X/Y offsets for a module by name."""
        slot = self.name_to_slot[name]
        d = self.slots[slot]
        return d["x_offset"], d["y_offset"]

    def get_slot(self, name: str):
        """Return the tray slot number for this module."""
        return self.name_to_slot[name]

    def list_modules(self):
        """Return a list of registered module names."""
        return list(self.name_to_slot.keys())



