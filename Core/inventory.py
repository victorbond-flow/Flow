import json
from pathlib import Path


class Inventory:
    def __init__(self, path=None):
        repo_root = Path(__file__).resolve().parent.parent
        self.path = Path(path or repo_root / "Core" / "inventory.json")
        self.slots = {}

        if self.path.exists():
            self.load()

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _slot_key(self, module, vial):
        return f"{module}:{int(vial)}"

    def _find_name(self, name):
        for key, record in self.slots.items():
            if record["name"] == name:
                return key, record
        return None, None

    # ---------------------------------------------------------
    # Core methods
    # ---------------------------------------------------------

    def assign(
        self,
        module,
        vial,
        name,
        concentration_M=None,
        solvent=None,
        current_volume_uL=None,
        min_safe_volume_uL=0,
    ):
        key = self._slot_key(module, vial)

        self.slots[key] = {
            "module": module,
            "vial": int(vial),
            "name": name,
            "concentration_M": concentration_M,
            "solvent": solvent,
            "current_volume_uL": current_volume_uL,
            "min_safe_volume_uL": min_safe_volume_uL,
        }

        self.save()

    def clear_slot(self, module, vial):
        key = self._slot_key(module, vial)

        if key in self.slots:
            del self.slots[key]
            self.save()

    def lookup(self, name):
        _, record = self._find_name(name)

        if record is None:
            raise KeyError(f"{name} not found in inventory")

        return record

    def get_slot(self, module, vial):
        key = self._slot_key(module, vial)

        if key not in self.slots:
            raise KeyError(f"{module} vial {vial} empty")

        return self.slots[key]

    def reserve(self, name, volume_uL):
        key, record = self._find_name(name)

        if record is None:
            raise KeyError(f"{name} not found")

        if record["current_volume_uL"] is None:
            return

        remaining = record["current_volume_uL"] - float(volume_uL)

        if remaining < record["min_safe_volume_uL"]:
            raise ValueError(
                f"Insufficient safe volume for {name}"
            )

        self.slots[key]["current_volume_uL"] = remaining
        self.save()

    def status(self):
        if not self.slots:
            print("Inventory empty")
            return

        for key, record in self.slots.items():
            print(
                f"{key} | {record['name']} | "
                f"{record['current_volume_uL']} uL remaining"
            )

    # ---------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------

    def save(self):
        self.path.write_text(json.dumps(self.slots, indent=2))

    def load(self):
        self.slots = json.loads(self.path.read_text())