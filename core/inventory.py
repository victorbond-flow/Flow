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

    def find_all(self, name):
        matches = []
    
        for key, record in self.slots.items():
            if record["name"] == name:
                matches.append((key, record))
    
        return matches

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

    def lookup(
        self,
        name,
        concentration_M=None,
        solvent=None,
    ):
        """
        Return the first matching vial.
    
        Used when a single source is sufficient.
        """
    
        matches = []
    
        for _, record in self.find_all(name):
    
            if (
                concentration_M is not None
                and record["concentration_M"] != concentration_M
            ):
                continue
    
            if (
                solvent is not None
                and record["solvent"] != solvent
            ):
                continue
    
            matches.append(record)
    
        if not matches:
            raise KeyError(
                f"{name} "
                f"(conc={concentration_M}, solvent={solvent}) "
                "not found"
            )
    
        matches.sort(
            key=lambda r: (
                r["module"],
                r["vial"]
            )
        )
    
        return matches[0]

    def get_slot(self, module, vial):
        key = self._slot_key(module, vial)

        if key not in self.slots:
            raise KeyError(f"{module} vial {vial} empty")

        return self.slots[key]

    def reserve(
        self,
        name,
        volume_uL,
        concentration_M=None,
        solvent=None,
    ):
    
        self.reserve_many([
            (
                name,
                volume_uL,
                concentration_M,
                solvent,
            )
        ])

    def reserve_many(self, reservations):

        for request in reservations:
    
            if len(request) == 2:
    
                name, volume_uL = request
                concentration_M = None
                solvent = None
    
            else:
    
                (
                    name,
                    volume_uL,
                    concentration_M,
                    solvent,
                ) = request
    
            source = self.find_source(
                name=name,
                volume_uL=volume_uL,
                concentration_M=concentration_M,
                solvent=solvent,
            )
    
            key = self._slot_key(
                source["module"],
                source["vial"]
            )
    
            self.slots[key]["current_volume_uL"] -= (
                float(volume_uL)
            )
    
        self.save()

    def check_available(
    self,
    name,
    volume_uL,
    concentration_M=None,
    solvent=None,
):
        try:
    
            self.find_source(
                name=name,
                volume_uL=volume_uL,
                concentration_M=concentration_M,
                solvent=solvent,
            )
    
            return True
    
        except Exception:
    
            return False

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

    # ---------------------------------------------------------
    # Planning (non-mutating)
    # ---------------------------------------------------------

    def find_source(
    self,
    name,
    volume_uL,
    concentration_M=None,
    solvent=None,
):
        """
        Find a single vial capable of satisfying the request.
    
        Matching:
            - name
            - concentration_M
            - solvent
    
        Returns:
            {
                "module": ...,
                "vial": ...,
                "volume_uL": ...
            }
    
        Does NOT mutate inventory.
        """
    
        if float(volume_uL) <= 0:
            raise ValueError(
                "Requested volume must be > 0"
            )
    
        candidates = []
    
        for _, record in self.find_all(name):
    
            # ---------------------------------------------
            # Chemical identity matching
            # ---------------------------------------------
            if (
                concentration_M is not None
                and record["concentration_M"] != concentration_M
            ):
                continue
    
            if (
                solvent is not None
                and record["solvent"] != solvent
            ):
                continue
    
            # ---------------------------------------------
            # Volume availability
            # ---------------------------------------------
            available = record["current_volume_uL"]
    
            if available is None:
                continue
    
            usable = (
                available
                - record["min_safe_volume_uL"]
            )
    
            # vial must satisfy ENTIRE request
            if usable >= volume_uL:
    
                candidates.append(
                    {
                        "module": record["module"],
                        "vial": record["vial"],
                        "usable_uL": usable,
                    }
                )
    
        # deterministic ordering
        candidates.sort(
            key=lambda x: (
                x["module"],
                x["vial"]
            )
        )
    
        if not candidates:
    
            raise ValueError(
                f"No vial can satisfy "
                f"{volume_uL} uL of {name} "
                f"(conc={concentration_M}, "
                f"solvent={solvent})"
            )
    
        selected = candidates[0]
    
        return {
            "module": selected["module"],
            "vial": selected["vial"],
            "volume_uL": float(volume_uL),
        }

    def allocate_sources(
    self,
    name,
    volume_uL,
    concentration_M=None,
    solvent=None,
):
        """
        Deterministically allocate required volume across vials.
        NO rollover logic. NO optimisation. Just ordered depletion.
        """
    
        if volume_uL <= 0:
            raise ValueError("Requested volume must be > 0")
    
        # gather candidates
        candidates = []
    
        for _, record in self.find_all(name):
    
            if concentration_M is not None and record["concentration_M"] != concentration_M:
                continue
    
            if solvent is not None and record["solvent"] != solvent:
                continue
    
            if record["current_volume_uL"] is None:
                continue
    
            usable = record["current_volume_uL"] - record["min_safe_volume_uL"]
    
            if usable > 0:
                candidates.append({
                    "module": record["module"],
                    "vial": record["vial"],
                    "usable": usable,
                })
    
        # deterministic ordering
        candidates.sort(key=lambda x: (x["module"], x["vial"]))
    
        remaining = float(volume_uL)
        plan = []
    
        for c in candidates:
            if remaining <= 0:
                break
    
            take = min(c["usable"], remaining)
    
            if take > 0:
                plan.append({
                    "module": c["module"],
                    "vial": c["vial"],
                    "volume_uL": float(take),
                })
    
                remaining -= take
    
        if remaining > 1e-9:
            raise ValueError(
                f"Insufficient {name}: need {volume_uL}, short by {remaining:.2f} uL"
            )
    
        return plan
            
