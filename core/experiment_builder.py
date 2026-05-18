from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json
import random
import pandas as pd

# TODO - Make preview inventory-aware (safety checks for volume consumption from vials? is that a bit much or what? idk)


class ExperimentBuilder:
    """
    Builds validated experiment plans + folders.

    v2.1 cleanup:
    - Single source of truth: self.rows
    - Fixed add_slug_set inconsistency
    - Added preview() execution trace
    """

    REQUIRED_GLOBAL_CONDITIONS = {
        "flowrate_ul_min": float,
        "gas_prime_s": float,
        "withdraw_rate_ml_min": float,
        "dispense_rate_ml_min": float,
        "needle_wash_volume_ul": float,
        "between_slug_wash_volume_ul": float,
    }

    def __init__(self, experiments_root=None, inventory=None):
        repo_root = Path(__file__).resolve().parent.parent
        self.experiments_root = Path(
            experiments_root or repo_root / "Experiments"
        )

        self.inventory = inventory

        # single source of truth for stateful builder
        self.rows = []
        self.slug_counter = 1

    # =========================================================
    # Stateful API
    # =========================================================

    def clear(self):
        self.rows = []
        self.slug_counter = 1

    def _next_slug_id(self):
        slug_id = f"slug_{self.slug_counter}"
        self.slug_counter += 1
        return slug_id

    def add_slug(self, components):
        if self.inventory is None:
            raise ValueError("Inventory required for add_slug")
    
        slug_id = self._next_slug_id()
        resolved = []
    
        # 1. resolve + validate first (NO state mutation yet)
        for component_order, (name, volume_uL) in enumerate(components, start=1):
            volume_uL = float(volume_uL)
    
            if volume_uL <= 0:
                raise ValueError(f"{name}: volume_uL must be > 0")
    
            record = self.inventory.lookup(name)
    
            resolved.append({
                "component": name,
                "component_order": component_order,
                "module": record["module"],
                "vial": record["vial"],
                "volume_uL": volume_uL,
            })
    
        # 2. reserve in one atomic step
        self.inventory.reserve_many(
            (r["component"], r["volume_uL"]) for r in resolved
        )
    
        # 3. commit to rows (single source of truth)
        for r in resolved:
            self.rows.append({
                "slug_id": slug_id,
                "slug_order": self.slug_counter - 1,
                "component_order": r["component_order"],
                "component": r["component"],
                "module": r["module"],
                "vial": r["vial"],
                "volume_uL": r["volume_uL"],
            })
    
        return slug_id

    def add_repeated_slug(self, components, n):
        return [self.add_slug(components) for _ in range(int(n))]

    def add_slug_set(
        self,
        df,
        component_map,
        fixed_total_volume_uL=None,
        slug_prefix="slug",
    ):
        """
        Each row = one slug
        """

        if self.inventory is None:
            raise ValueError("Inventory required for add_slug_set")

        if hasattr(df, "to_dict"):
            rows = df.to_dict(orient="records")
        else:
            rows = list(df)

        for row in rows:
            slug_id = f"{slug_prefix}_{self.slug_counter}"

            components = []
            total_volume = 0.0
            reservations = []

            for column, material_name in component_map.items():
                if column not in row:
                    raise KeyError(f"Missing column: {column}")

                volume = float(row[column])

                if volume <= 0:
                    continue

                record = self.inventory.lookup(material_name)

                components.append({
                    "component": material_name,
                    "module": record["module"],
                    "vial": record["vial"],
                    "volume_uL": volume,
                })

                total_volume += volume
                reservations.append((material_name, volume))

            if fixed_total_volume_uL is not None:
                if abs(total_volume - float(fixed_total_volume_uL)) > 1e-6:
                    raise ValueError(
                        f"{slug_id} total volume mismatch"
                    )

            self.inventory.reserve_many(reservations)

            for i, comp in enumerate(components, start=1):
                self.rows.append({
                    "slug_id": slug_id,
                    "slug_order": self.slug_counter,
                    "component_order": i,
                    "component": comp["component"],
                    "module": comp["module"],
                    "vial": comp["vial"],
                    "volume_uL": comp["volume_uL"],
                })

            self.slug_counter += 1

    def randomise(self):
        grouped = {}

        for row in self.rows:
            grouped.setdefault(row["slug_id"], []).append(row)

        slug_groups = list(grouped.values())
        random.shuffle(slug_groups)

        new_rows = []

        for slug_order, group in enumerate(slug_groups, start=1):
            for row in group:
                r = dict(row)
                r["slug_order"] = slug_order
                new_rows.append(r)

        self.rows = new_rows

    def create_experiment(
        self,
        experiment_id,
        description="",
        global_conditions=None,
        overwrite=False,
    ):
        return self.build_and_create(
            experiment_id=experiment_id,
            rows=self.rows,
            description=description,
            global_conditions=global_conditions,
            overwrite=overwrite,
        )

    # =========================================================
    # Core build
    # =========================================================

    def _coerce_rows(self, rows):
        if hasattr(rows, "to_dict"):
            rows = rows.to_dict(orient="records")

        if not isinstance(rows, list):
            raise TypeError("rows must be a list of dicts or a pandas DataFrame")

        coerced = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise TypeError("Each row must be a dict")

            coerced_row = dict(row)
            coerced_row["_input_order"] = index
            coerced.append(coerced_row)

        if not coerced:
            raise ValueError("Cannot build an experiment with no rows")

        return coerced

    def _validate_row(self, row):
        required = ("slug_id", "module", "vial", "volume_uL")
        missing = [k for k in required if k not in row]
        if missing:
            raise ValueError(f"Missing: {missing}")

        if self._is_missing(row["slug_id"]) or row["slug_id"] == "":
            raise ValueError("slug_id must not be empty")

        if self._is_missing(row["module"]) or row["module"] == "":
            raise ValueError(f"{row['slug_id']}: module must be resolved")

        if self._is_missing(row["vial"]):
            raise ValueError(f"{row['slug_id']}: vial must be resolved")

        try:
            int(row["vial"])
        except Exception as exc:
            raise ValueError(f"{row['slug_id']}: vial must be an integer") from exc

        try:
            volume = float(row["volume_uL"])
        except Exception as exc:
            raise ValueError(f"{row['slug_id']}: volume_uL must be numeric") from exc

        if volume <= 0:
            raise ValueError(f"{row['slug_id']}: volume_uL must be > 0")

    def _validate_rows_integrity(self, rows):
        required = ("slug_id", "module", "vial", "volume_uL")
    
        for i, r in enumerate(rows):
            missing = [k for k in required if k not in r]
            if missing:
                raise ValueError(f"Row {i} missing fields: {missing}")
    
            if r.get("slug_id") in (None, "", []):
                raise ValueError(f"Row {i}: slug_id invalid")
    
            if self._is_missing(r.get("module")):
                raise ValueError(f"Row {i}: module unresolved")
    
            if self._is_missing(r.get("vial")):
                raise ValueError(f"Row {i}: vial unresolved")
    
            try:
                int(r["vial"])
            except Exception:
                raise ValueError(f"Row {i}: vial must be integer")
    
            try:
                v = float(r["volume_uL"])
            except Exception:
                raise ValueError(f"Row {i}: volume_uL must be numeric")
    
            if v <= 0:
                raise ValueError(f"Row {i}: volume_uL must be > 0")

    def _validate_global_conditions(self, global_conditions):
        if global_conditions is None:
            raise ValueError("global_conditions required")

        missing = [
            key
            for key in self.REQUIRED_GLOBAL_CONDITIONS
            if key not in global_conditions
        ]
        if missing:
            raise ValueError(f"Missing global_conditions fields: {missing}")

        cleaned = {}
        for key, typ in self.REQUIRED_GLOBAL_CONDITIONS.items():
            try:
                value = typ(global_conditions[key])
            except Exception as exc:
                raise ValueError(
                    f"global_conditions[{key}] must be {typ.__name__}"
                ) from exc

            if value <= 0:
                raise ValueError(f"global_conditions[{key}] must be > 0")

            cleaned[key] = value

        return cleaned

    def build_plan(
    self,
    experiment_id,
    rows,
    description="",
    global_conditions=None,
):
        rows = self._coerce_rows(rows)
        global_conditions = self._validate_global_conditions(global_conditions)
    
        # NEW: structural integrity gate (replaces scattered validation)
        self._validate_rows_integrity(rows)
    
        ordered_rows = sorted(
            rows,
            key=lambda r: (
                self._order_value(r, "slug_order"),
                self._order_value(r, "component_order"),
                r["_input_order"],
            ),
        )
    
        slugs = {}
        slug_sequence = []
    
        for r in ordered_rows:
            sid = r["slug_id"]
    
            if sid not in slugs:
                slugs[sid] = {
                    "slug_id": sid,
                    "reaction_plan": []
                }
                slug_sequence.append(slugs[sid])
    
            component = {
                "module": r["module"],
                "vial": int(r["vial"]),
                "volume_uL": float(r["volume_uL"]),
            }
    
            if not self._is_missing(r.get("component")):
                component["component"] = r["component"]
    
            if not self._is_missing(r.get("block_id")):
                component["block_id"] = r["block_id"]
    
            slugs[sid]["reaction_plan"].append(component)
    
        return {
            "experiment_id": experiment_id,
            "description": description,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "global_conditions": global_conditions,
            "slugs": slug_sequence,
        }

    # =========================================================
    # Folder creation
    # =========================================================

    def create_experiment_folder(self, plan, overwrite=False):
        exp_dir = self.experiments_root / plan["experiment_id"]

        if exp_dir.exists() and not overwrite:
            raise FileExistsError(exp_dir)

        exp_dir.mkdir(parents=True, exist_ok=True)

        (exp_dir / "plan.json").write_text(json.dumps(plan, indent=2))

        log = {
            "experiment_id": plan["experiment_id"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "events": [],
        }

        (exp_dir / "log.json").write_text(json.dumps(log, indent=2))

        return {
            "experiment_dir": exp_dir,
            "plan_path": exp_dir / "plan.json",
            "log_path": exp_dir / "log.json",
        }

    # =========================================================
    # Summary
    # =========================================================

    def summarise_plan(self, plan):
        out = []

        for s in plan["slugs"]:
            total = sum(c["volume_uL"] for c in s["reaction_plan"])

            out.append({
                "slug_id": s["slug_id"],
                "num_components": len(s["reaction_plan"]),
                "total_volume_uL": total,
                "components": [
                    (
                        c.get("component"),
                        c["module"],
                        c["vial"],
                        c["volume_uL"],
                    )
                    for c in s["reaction_plan"]
                ]
            })

        return out

    # =========================================================
    # NEW: preview layer
    # =========================================================

    def preview(self, plan):
        """
        Execution-level view: what will actually happen step-by-step.
        """

        rows = []

        for slug in plan["slugs"]:
            for i, comp in enumerate(slug["reaction_plan"], start=1):
                rows.append({
                    "slug_id": slug["slug_id"],
                    "step": i,
                    "component": comp.get("component"),
                    "module": comp["module"],
                    "vial": comp["vial"],
                    "volume_uL": comp["volume_uL"],
                })

        return pd.DataFrame(rows)

    # =========================================================
    # Final API
    # =========================================================

    def build_and_create(
        self,
        experiment_id,
        rows,
        description="",
        global_conditions=None,
        overwrite=False,
    ):
        plan = self.build_plan(
            experiment_id,
            rows,
            description,
            global_conditions,
        )

        paths = self.create_experiment_folder(plan, overwrite)

        return {
            "plan": plan,
            "summary": self.summarise_plan(plan),
            "preview": self.preview(plan),
            **paths,
        }

    def _is_missing(self, value):
        return value is None or pd.isna(value)

    def _order_value(self, row, key):
        value = row.get(key)
        if self._is_missing(value):
            return row["_input_order"]
        return value
