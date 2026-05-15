from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd
from collections import defaultdict
import copy


@dataclass
class CompiledRow:
    slug_id: str
    module: str
    vial: int
    volume_uL: float

    component: str
    concentration_M: Optional[float] = None
    solvent: Optional[str] = None

    block_id: Optional[str] = None
    slug_order: Optional[int] = None
    component_order: Optional[int] = None


class ExperimentCompiler:
    """
    Translates ExperimentIntent → physical slug dataframe.

    Responsibilities:
    - Resolve chemical names via Inventory
    - Expand blocks into slug-level rows
    - Output Builder-compatible dataframe

    This is NOT concerned with:
    - hardware execution
    - JSON formatting
    - scheduling
    """

    def __init__(self, inventory, trace=False):
        self.inventory = inventory
        self.trace = trace

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    OUTPUT_COLUMNS = [
        "slug_id",
        "module",
        "vial",
        "volume_uL",
    
        "component",
        "concentration_M",
        "solvent",
    
        "block_id",
        "slug_order",
        "component_order",
    ]

    def compile(self, intent: Dict[str, Any]) -> pd.DataFrame:
        shadow = {
            key: (
                record["current_volume_uL"] - record["min_safe_volume_uL"]
                if record["current_volume_uL"] is not None
                else 0.0
            )
            for key, record in self.inventory.slots.items()
        }
        intent = self._coerce_intent(intent)
    
        rows = []
        experiment_id = intent.get("experiment_id", "EXPT")
        blocks = intent["blocks"]
    
        for block_index, block in enumerate(blocks):
            block_rows = self._expand_block(
                block=block,
                block_index=block_index,
                experiment_id=experiment_id,
                shadow=shadow
            )
            rows.extend(block_rows)
    
        if not rows:
            raise ValueError("Compilation produced no rows")
    
        # ------------------------------------------------------------
        # NEW: global feasibility gate (non-mutating)
        # ------------------------------------------------------------
        feasibility_report = self._validate_global_feasibility(rows)
    
        if feasibility_report["status"] == "infeasible":
            raise ValueError(feasibility_report["message"])
    
        # enforce strict schema BEFORE dataframe conversion
        data = [r.__dict__ for r in rows]
    
        for i, r in enumerate(data):
            missing = [c for c in self.OUTPUT_COLUMNS if c not in r]
            if missing:
                raise ValueError(f"Row {i} missing columns: {missing}")
    
        return pd.DataFrame(data)[self.OUTPUT_COLUMNS]

    def normalise(self, experiment_id, slug_spec, block_id="block_1"):
        """
        Convert a compact slug specification into canonical experiment intent.
    
        Purpose
        -------
        This is a structural transformation layer only.
        It does NOT interpret chemistry, ratios, or experimental meaning.
    
        Input format (human-friendly):
            [
                ("slug_1", [("MeCN", 20), ("MeCN", 80)]),
                ...
            ]
    
        Output format (compiler-ready intent):
            {
                "experiment_id": ...,
                "blocks": [
                    {
                        "block_id": ...,
                        "slugs": [
                            {
                                "slug_id": ...,
                                "composition": [...]
                            }
                        ]
                    }
                ]
            }
        """
    
        # Basic structural conversion
        if not slug_spec:
            raise ValueError("slug_spec must contain at least one slug")

        slugs = []
        for slug_id, composition in slug_spec:
            if not composition:
                raise ValueError(f"{slug_id} has no components")

            slugs.append({
                "slug_id": slug_id,
                "composition": composition
            })
    
        intent = {
            "experiment_id": experiment_id,
            "blocks": [
                {
                    "block_id": block_id,
                    "slugs": slugs
                }
            ]
        }
    
        return intent

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _trace(self, message):
        if self.trace:
            print(message)

    def _coerce_intent(self, intent):
        if isinstance(intent, dict):
            coerced = intent
        elif hasattr(intent, "experiment_id") and hasattr(intent, "blocks"):
            coerced = {
                "experiment_id": intent.experiment_id,
                "blocks": intent.blocks,
            }
        else:
            raise TypeError("intent must be a dict or ExperimentIntent-like object")
    
        if "blocks" not in coerced or coerced["blocks"] is None:
            raise ValueError("Intent must contain blocks")
    
        if len(coerced["blocks"]) == 0:
            raise ValueError("Intent must contain at least one block")
    
        return coerced

    def summarise_slugs(self, df):
        grouped = df.groupby("slug_id")
    
        summary = pd.DataFrame({
            "slug_id": grouped.size().index,
            "n_components": grouped.size().values,
            "total_volume_uL": grouped["volume_uL"].sum().values,
            "components": [
                list(zip(group["component"].values, group["volume_uL"].values))
                for _, group in grouped
            ]
        })
    
        return summary

    def _build_insufficient_inventory_error(
    self,
    name,
    required_volume,
    candidates
):
        """
        Creates a human-readable failure message for the chemist.
        """
    
        total_available = sum(c["usable"] for c in candidates)
    
        lines = [
            f"\n❌ INSUFFICIENT INVENTORY: {name}",
            f"Required: {required_volume:.1f} µL",
            f"Available (usable): {total_available:.1f} µL",
            f"Shortfall: {required_volume - total_available:.1f} µL",
            "",
            "Breakdown:"
        ]
    
        for c in candidates:
            lines.append(
                f"  - rack {c['module']} vial {c['vial']}: {c['usable']:.1f} µL usable"
            )
    
        return "\n".join(lines)

    # ------------------------------------------------------------
    # Block expansion
    # ------------------------------------------------------------

    def _expand_block(self, block, block_index, experiment_id, shadow):
        block_id = block.get("block_id", f"block_{block_index + 1}")
    
        # ----------------------------
        # INTENT-STYLE BLOCK (NEW)
        # ----------------------------
        components = block.get("components")
        ratios = block.get("ratios")
        total_volume = block.get("total_volume_uL")
    
        if components is not None and ratios is not None:
            return self._expand_ratio_block(block, block_id, shadow)
    
        # ----------------------------
        # OLD SLUG-STYLE BLOCK (LEGACY)
        # ----------------------------
        slug_definitions = block.get("slugs")
    
        if slug_definitions is None:
            raise ValueError(f"{block_id} must contain slugs")
    
        if len(slug_definitions) == 0:
            raise ValueError(f"{block_id} has no slugs")
    
        expanded_rows = []
    
        for i, slug in enumerate(slug_definitions):
            slug_id = slug.get("slug_id", f"{block_id}_slug_{i + 1}")
    
            composition = slug.get("composition")
    
            if not composition:
                raise ValueError(f"{slug_id} has no composition")
    
            for j, item in enumerate(composition, start=1):
                component_data = self._normalise_component(item)

                component_name = component_data["name"]
                volume_uL = component_data["volume_uL"]
                concentration_M = component_data["concentration_M"]
                solvent = component_data["solvent"]
    
                resolved = self._resolve_component(
                    name=component_name,
                    volume_uL=volume_uL,
                    concentration_M=concentration_M,
                    solvent=solvent,
                    shadow=shadow
                )
    
                expanded_rows.append(
                    CompiledRow(
                        slug_id=slug_id,
                        module=resolved["module"],
                        vial=resolved["vial"],
                        volume_uL=float(volume_uL),
                
                        component=component_name,
                        concentration_M=concentration_M,
                        solvent=solvent,
                
                        block_id=block_id,
                        slug_order=i + 1,
                        component_order=j,
                    )
                )
    
        return expanded_rows

    def _expand_ratio_block(self, block, block_id, shadow):
        components = block.get("components", [])
        ratios = block.get("ratios", [])
        total_volume = float(block.get("total_volume_uL", 0))
    
        if not components:
            raise ValueError(f"{block_id} must define components")
    
        if total_volume <= 0:
            raise ValueError(f"{block_id}: total_volume_uL must be > 0")
    
        expanded_rows = []
    
        for i, ratio in enumerate(ratios, start=1):
    
            if len(ratio) != len(components):
                raise ValueError(
                    f"{block_id} ratio {ratio} does not match components {components}"
                )
    
            ratio_total = sum(float(v) for v in ratio)
    
            if ratio_total <= 0:
                raise ValueError(
                    f"{block_id} ratio total must be > 0"
                )
    
            slug_id = f"{block_id}_slug_{i}"
    
            for j, (component, ratio_value) in enumerate(
                zip(components, ratio),
                start=1
            ):
    
                volume = (
                    float(ratio_value) / ratio_total
                ) * total_volume
    
                # Backwards compatibility:
                # allow plain strings OR richer component definitions
                if isinstance(component, str):
    
                    component = {
                        "name": component,
                        "concentration_M": None,
                        "solvent": None,
                        "volume_uL": volume
                    }
    
                resolved = self._resolve_component(
                    name=component["name"],
                    volume_uL=volume,
                    concentration_M=component["concentration_M"],
                    solvent=component["solvent"],
                    shadow=shadow
                )
    
                expanded_rows.append(
                    CompiledRow(
                        slug_id=slug_id,
                        module=resolved["module"],
                        vial=resolved["vial"],
                        volume_uL=float(volume),
    
                        component=component["name"],
                        concentration_M=component["concentration_M"],
                        solvent=component["solvent"],
    
                        block_id=block_id,
                        slug_order=i,
                        component_order=j,
                    )
                )
    
        return expanded_rows

    def _normalise_component(self, item):
        if isinstance(item, dict):
            name = item.get("component") or item.get("name")
            volume = item.get("volume_uL") or item.get("volume")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            name, volume = item
        else:
            raise ValueError(f"Invalid component format: {item}")
    
        if not name:
            raise ValueError("Component missing name")
    
        try:
            volume = float(volume)
        except Exception:
            raise ValueError(f"{name}: volume must be numeric")
    
        if volume <= 0:
            raise ValueError(f"{name}: volume_uL must be > 0")
    
        return {
            "name": name,
            "volume_uL": volume,
            "concentration_M": item.get("concentration_M")
                if isinstance(item, dict)
                else None,
            "solvent": item.get("solvent")
                if isinstance(item, dict)
                else None,
        }

    # ------------------------------------------------------------
    # Inventory resolution + feasibility check
    # ------------------------------------------------------------

    def _resolve_component(
    self,
    name,
    volume_uL,
    concentration_M,
    solvent,
    shadow,
):
        """
        Deterministic resolver with optional trace output.
        """
    
        if volume_uL <= 0:
            raise ValueError("Requested volume must be > 0")
    
        self._trace(f"\n[RESOLVE] {name} | request={volume_uL} µL")
    
        candidates = []
    
        for key, record in self.inventory.find_all(name):
    
            if concentration_M is not None and record["concentration_M"] != concentration_M:
                continue
    
            if solvent is not None and record["solvent"] != solvent:
                continue
    
            available = record["current_volume_uL"]
    
            if available is None:
                continue
    
            usable = available - record["min_safe_volume_uL"]
    
            remaining = shadow.get(key, usable)
    
            self._trace(
                f"  candidate {key}: usable={usable:.1f}, remaining={remaining:.1f}"
            )
    
            if remaining >= volume_uL:
                candidates.append({
                    "key": key,
                    "module": record["module"],
                    "vial": record["vial"],
                    "remaining": remaining,
                })
    
        if not candidates:
            # rebuild full candidate list for diagnostics
            diagnostic_candidates = []
        
            for key, record in self.inventory.find_all(name):
        
                if concentration_M is not None and record["concentration_M"] != concentration_M:
                    continue
        
                if solvent is not None and record["solvent"] != solvent:
                    continue
        
                available = record["current_volume_uL"]
        
                if available is None:
                    continue
        
                usable = available - record["min_safe_volume_uL"]
        
                diagnostic_candidates.append({
                    "module": record["module"],
                    "vial": record["vial"],
                    "usable": usable,
                })
        
            message = self._build_insufficient_inventory_error(
                name=name,
                required_volume=volume_uL,
                candidates=diagnostic_candidates
            )
        
            raise ValueError(message)
    
        candidates.sort(key=lambda x: (x["module"], x["vial"]))
    
        selected = candidates[0]
        key = selected["key"]
    
        self._trace(
            f"  ✅ selected {key} (vial {selected['vial']}) "
            f"| remaining before={selected['remaining']:.1f}"
        )
    
        shadow[key] = shadow.get(key, selected["remaining"]) - volume_uL
    
        self._trace(
            f"  → remaining after={shadow[key]:.1f}"
        )
    
        return {
            "module": selected["module"],
            "vial": selected["vial"],
            "volume_uL": float(volume_uL),
        }


    def _validate_global_feasibility(self, rows):

        totals = defaultdict(float)
    
        for r in rows:
            key = (r.component, r.concentration_M, r.solvent)
            totals[key] += float(r.volume_uL)
    
        shortages = []
        limiting = []
    
        for (name, conc, solvent), required in totals.items():
    
            # -----------------------------------------
            # gather usable pool across all vials
            # -----------------------------------------
            candidates = []
    
            for _, record in self.inventory.find_all(name):
    
                if conc is not None and record["concentration_M"] != conc:
                    continue
    
                if solvent is not None and record["solvent"] != solvent:
                    continue
    
                available = record["current_volume_uL"]
    
                if available is None:
                    continue
    
                usable = available - record["min_safe_volume_uL"]
    
                if usable > 0:
                    candidates.append({
                        "module": record["module"],
                        "vial": record["vial"],
                        "usable": usable,
                    })
    
            total_available = sum(c["usable"] for c in candidates)
    
            if total_available < required:
                shortages.append({
                    "name": name,
                    "concentration_M": conc,
                    "solvent": solvent,
                    "required_uL": required,
                    "available_uL": total_available,
                })
                continue
    
            # -----------------------------------------
            # deterministic allocation (NO rollover logic)
            # -----------------------------------------
            candidates.sort(key=lambda x: (x["module"], x["vial"]))
    
            remaining = required
            plan = []
    
            for c in candidates:
                if remaining <= 0:
                    break
    
                take = min(c["usable"], remaining)
    
                plan.append({
                    "name": name,
                    "module": c["module"],
                    "vial": c["vial"],
                    "volume_uL": take,
                })
    
                remaining -= take
    
            limiting.append({
                "name": name,
                "plan": plan,
                "limiting_vial": max(plan, key=lambda x: x["volume_uL"]) if plan else None
            })
    
        if shortages:
            return {
                "status": "infeasible",
                "message": "Experiment infeasible:\n" + "\n".join(
                    f"- {s['name']}: need {s['required_uL']} uL, have {s['available_uL']} uL"
                    for s in shortages
                ),
                "shortages": shortages,
                "limiting": limiting,
            }
    
        return {
            "status": "feasible",
            "message": "OK",
            "shortages": [],
            "limiting": limiting,
        }
