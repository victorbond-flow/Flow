from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json


class ExperimentBuilder:
    """
    Build experiment folders from tabular-style slug component rows.

    Input rows may be a list of dicts or a pandas DataFrame with columns:
    - slug_id
    - module
    - vial
    - volume_uL

    Optional columns:
    - pickup_rate
    - slug_order
    - component_order
    """

    def __init__(self, experiments_root=None):
        repo_root = Path(__file__).resolve().parent.parent
        self.experiments_root = Path(experiments_root or repo_root / "Experiments")

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
        missing = [key for key in required if key not in row]
        if missing:
            raise ValueError(f"Row is missing required fields: {missing}")

        volume = float(row["volume_uL"])
        if volume <= 0:
            raise ValueError("volume_uL must be positive.")

    def build_plan(self, experiment_id, rows, description="", global_conditions=None):
        rows = self._coerce_rows(rows)
        global_conditions = deepcopy(global_conditions or {})

        for row in rows:
            self._validate_row(row)

        ordered_rows = sorted(
            rows,
            key=lambda row: (
                row.get("slug_order", row["_input_order"]),
                row.get("component_order", row["_input_order"]),
                row["_input_order"],
            ),
        )

        slugs_by_id = {}
        slug_sequence = []

        for row in ordered_rows:
            slug_id = row["slug_id"]

            if slug_id not in slugs_by_id:
                slug = {"slug_id": slug_id, "reaction_plan": []}
                slugs_by_id[slug_id] = slug
                slug_sequence.append(slug)

            component = {
                "module": row["module"],
                "vial": int(row["vial"]),
                "volume_uL": float(row["volume_uL"]),
            }

            if "pickup_rate" in row and row["pickup_rate"] is not None:
                component["rate"] = float(row["pickup_rate"])

            slugs_by_id[slug_id]["reaction_plan"].append(component)

        return {
            "experiment_id": experiment_id,
            "description": description,
            "global_conditions": global_conditions,
            "slugs": slug_sequence,
        }

    def plan_to_rows(self, plan):
        rows = []

        for slug_order, slug in enumerate(plan.get("slugs", []), start=1):
            for component_order, component in enumerate(
                slug.get("reaction_plan", []),
                start=1,
            ):
                rows.append(
                    {
                        "slug_id": slug["slug_id"],
                        "slug_order": slug_order,
                        "component_order": component_order,
                        "module": component["module"],
                        "vial": component["vial"],
                        "volume_uL": component.get("volume_uL", component.get("volume")),
                        "pickup_rate": component.get("rate"),
                    }
                )

        return rows

    def summarise_plan(self, plan):
        summary = []

        for slug in plan.get("slugs", []):
            reaction_plan = slug.get("reaction_plan", [])
            total_volume = sum(
                component.get("volume_uL", component.get("volume", 0.0))
                for component in reaction_plan
            )

            components = ", ".join(
                f"{component['module']}:{component['vial']} ({component.get('volume_uL', component.get('volume'))} uL)"
                for component in reaction_plan
            )

            summary.append(
                {
                    "slug_id": slug["slug_id"],
                    "num_components": len(reaction_plan),
                    "total_volume_uL": total_volume,
                    "components": components,
                }
            )

        return summary

    def create_experiment_folder(self, plan, overwrite=False):
        experiment_id = plan["experiment_id"]
        exp_dir = self.experiments_root / experiment_id

        if exp_dir.exists() and not overwrite:
            raise FileExistsError(
                f"Experiment folder already exists: {exp_dir}. "
                "Use overwrite=True to replace the plan/log files."
            )

        exp_dir.mkdir(parents=True, exist_ok=True)

        plan_path = exp_dir / "plan.json"
        log_path = exp_dir / "log.json"

        with open(plan_path, "w") as f:
            json.dump(plan, f, indent=2)

        log_payload = {
            "experiment_id": experiment_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "events": [],
        }

        with open(log_path, "w") as f:
            json.dump(log_payload, f, indent=2)

        return {
            "experiment_dir": exp_dir,
            "plan_path": plan_path,
            "log_path": log_path,
        }

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
