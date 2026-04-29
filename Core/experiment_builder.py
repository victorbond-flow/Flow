from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json


class ExperimentBuilder:
    """
    Builds validated experiment plans + folders.

    Key upgrade:
    - global_conditions schema is now enforced
    - flowrate_ul_min is REQUIRED (no silent defaults downstream)
    - ensures execution layer is deterministic and reproducible
    """

    REQUIRED_GLOBAL_CONDITIONS = {
        "flowrate_ul_min": float,
        "gas_prime_s": float,
    }

    def __init__(self, experiments_root=None):
        repo_root = Path(__file__).resolve().parent.parent
        self.experiments_root = Path(experiments_root or repo_root / "Experiments")

    # ------------------------------------------------------------------
    # Row handling
    # ------------------------------------------------------------------

    def _coerce_rows(self, rows):
        if hasattr(rows, "to_dict"):
            rows = rows.to_dict(orient="records")

        if not isinstance(rows, list):
            raise TypeError("rows must be a list of dicts or a pandas DataFrame.")

        coerced = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise TypeError("Each row must be a dict.")

            coerced_row = dict(row)
            coerced_row["_input_order"] = index
            coerced.append(coerced_row)

        return coerced

    def _validate_row(self, row):
        required = ("slug_id", "module", "vial", "volume_uL")
        missing = [k for k in required if k not in row]
        if missing:
            raise ValueError(f"Row missing fields: {missing}")

        volume = float(row["volume_uL"])
        if volume <= 0:
            raise ValueError("volume_uL must be > 0")

    # ------------------------------------------------------------------
    # Global condition validation (NEW)
    # ------------------------------------------------------------------

    def _validate_global_conditions(self, global_conditions):
        if global_conditions is None:
            raise ValueError(
                "global_conditions is required (must include flowrate_ul_min, gas_prime_s)"
            )

        missing = []
        for key in self.REQUIRED_GLOBAL_CONDITIONS:
            if key not in global_conditions:
                missing.append(key)

        if missing:
            raise ValueError(
                f"Missing global_conditions fields: {missing}"
            )

        # type coercion + validation
        cleaned = {}
        for key, typ in self.REQUIRED_GLOBAL_CONDITIONS.items():
            try:
                cleaned[key] = typ(global_conditions[key])
            except Exception:
                raise ValueError(
                    f"global_conditions[{key}] must be {typ.__name__}"
                )

        return cleaned

    # ------------------------------------------------------------------
    # Plan builder
    # ------------------------------------------------------------------

    def build_plan(self, experiment_id, rows, description="", global_conditions=None):

        rows = self._coerce_rows(rows)
        global_conditions = self._validate_global_conditions(global_conditions)

        for row in rows:
            self._validate_row(row)

        ordered_rows = sorted(
            rows,
            key=lambda r: (
                r.get("slug_order", r["_input_order"]),
                r.get("component_order", r["_input_order"]),
                r["_input_order"],
            ),
        )

        slugs_by_id = {}
        slug_sequence = []

        for row in ordered_rows:
            slug_id = row["slug_id"]

            if slug_id not in slugs_by_id:
                slug = {
                    "slug_id": slug_id,
                    "reaction_plan": []
                }
                slugs_by_id[slug_id] = slug
                slug_sequence.append(slug)

            component = {
                "module": row["module"],
                "vial": int(row["vial"]),
                "volume_uL": float(row["volume_uL"]),
            }

            if row.get("pickup_rate") is not None:
                component["rate"] = float(row["pickup_rate"])

            slugs_by_id[slug_id]["reaction_plan"].append(component)

        return {
            "experiment_id": experiment_id,
            "description": description,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "global_conditions": global_conditions,
            "slugs": slug_sequence,
        }

    # ------------------------------------------------------------------
    # Folder creation
    # ------------------------------------------------------------------

    def create_experiment_folder(self, plan, overwrite=False):
        experiment_id = plan["experiment_id"]
        exp_dir = self.experiments_root / experiment_id

        if exp_dir.exists() and not overwrite:
            raise FileExistsError(f"Experiment exists: {exp_dir}")

        exp_dir.mkdir(parents=True, exist_ok=True)

        (exp_dir / "plan.json").write_text(json.dumps(plan, indent=2))

        log_payload = {
            "experiment_id": experiment_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "events": [],
        }

        (exp_dir / "log.json").write_text(json.dumps(log_payload, indent=2))

        return {
            "experiment_dir": exp_dir,
            "plan_path": exp_dir / "plan.json",
            "log_path": exp_dir / "log.json",
        }

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def summarise_plan(self, plan):
        summary = []

        for slug in plan.get("slugs", []):
            reaction_plan = slug.get("reaction_plan", [])

            total_volume = sum(
                c.get("volume_uL", c.get("volume", 0.0))
                for c in reaction_plan
            )

            components = ", ".join(
                f"{c['module']}:{c['vial']} ({c['volume_uL']} uL)"
                for c in reaction_plan
            )

            summary.append({
                "slug_id": slug["slug_id"],
                "num_components": len(reaction_plan),
                "total_volume_uL": total_volume,
                "components": components,
            })

        return summary

    def build_and_create(
        self,
        experiment_id,
        rows,
        description="",
        global_conditions=None,
        overwrite=False,
    ):
        plan = self.build_plan(
            experiment_id=experiment_id,
            rows=rows,
            description=description,
            global_conditions=global_conditions,
        )

        paths = self.create_experiment_folder(plan, overwrite=overwrite)

        return {
            "plan": plan,
            "summary": self.summarise_plan(plan),
            **paths,
        }
