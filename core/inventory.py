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

        reservation_plan = []
    
        # temporary state for planning
        temp_slots = {
            k: v.copy()
            for k, v in self.slots.items()
        }
    
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
    
            # temporarily swap inventory state
            original = self.slots
            self.slots = temp_slots
    
            plan = self.plan_sources(
                name=name,
                volume_uL=volume_uL,
                concentration_M=concentration_M,
                solvent=solvent,
            )
    
            # apply immediately to temp state
            for source in plan:
    
                key = self._slot_key(
                    source["module"],
                    source["vial"]
                )
    
                temp_slots[key]["current_volume_uL"] -= (
                    source["volume_uL"]
                )
    
            reservation_plan.extend(plan)
    
            self.slots = original
    
        # commit real state
        for source in reservation_plan:
    
            key = self._slot_key(
                source["module"],
                source["vial"]
            )
    
            self.slots[key]["current_volume_uL"] -= (
                source["volume_uL"]
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
    
            self.plan_sources(
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

    def plan_sources(
        self,
        name: str,
        volume_uL: float,
        concentration_M=None,
        solvent=None,
    ):
        """
            Plan how to source a required volume of a chemically-defined reagent
            across multiple vials in deterministic order.
        
            Matching is based on:
                - name
                - solvent
                - concentration_M
        
            Does NOT mutate inventory.
            """
        
            if volume_uL <= 0:
                raise ValueError("Requested volume must be > 0")
        
            candidates = []
        
            for key, record in self.slots.items():
        
                # -----------------------------------------------------
                # chemical identity filter
                # -----------------------------------------------------
                if record["name"] != name:
                    continue
        
                if solvent is not None and record["solvent"] != solvent:
                    continue
        
                if concentration_M is not None and record["concentration_M"] != concentration_M:
                    continue
        
                # -----------------------------------------------------
                # usable volume check
                # -----------------------------------------------------
                available = record["current_volume_uL"]
        
                if available is None:
                    raise RuntimeError(
                        f"{name}: vial {record['module']}:{record['vial']} "
                        "has unknown volume"
                    )
        
                usable = available - record["min_safe_volume_uL"]
        
                if usable > 0:
                    candidates.append(
                        {
                            "module": record["module"],
                            "vial": record["vial"],
                            "usable_uL": usable,
                        }
                    )
        
            # FIFO ordering (stable + deterministic)
            candidates.sort(key=lambda x: (x["module"], x["vial"]))
        
            remaining = float(volume_uL)
            plan = []
        
            for c in candidates:
        
                if remaining <= 0:
                    break
        
                take = min(c["usable_uL"], remaining)
        
                if take > 0:
                    plan.append(
                        {
                            "module": c["module"],
                            "vial": c["vial"],
                            "volume_uL": float(take),
                        }
                    )
        
                    remaining -= take
        
            if remaining > 1e-9:
                raise ValueError(
                    f"Insufficient {name} "
                    f"(solvent={solvent}, conc={concentration_M}): "
                    f"short by {remaining:.2f} uL above safety limits"
                )
        
            return plan
            
