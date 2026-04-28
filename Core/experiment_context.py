from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from datetime import datetime
import json


@dataclass
class ExperimentContext:
    experiment_id: str
    plan: dict
    slug_index: int
    log_path: Path
    state: str   # prepared / running


class ExperimentManager:
    def __init__(self):
        self.mode = "untracked"
        self.context: Optional[ExperimentContext] = None

        # repo root = parent of Core/
        self.repo_root = Path(__file__).resolve().parent.parent
        self.experiments_root = self.repo_root / "Experiments"

    def load_experiment(self, experiment_id: str):
        if self.context is not None:
            raise Exception(
                f"Experiment already loaded: {self.context.experiment_id}"
            )

        exp_dir = self.experiments_root / experiment_id

        if not exp_dir.exists():
            raise FileNotFoundError(f"Experiment folder not found: {exp_dir}")

        plan_path = exp_dir / "plan.json"
        log_path = exp_dir / "log.json"

        if not plan_path.exists():
            raise FileNotFoundError(f"Missing plan.json for {experiment_id}")

        with open(plan_path, "r") as f:
            plan = json.load(f)

        if not log_path.exists():
            with open(log_path, "w") as f:
                json.dump({"experiment_id": experiment_id, "events": []}, f, indent=2)

        self.context = ExperimentContext(
            experiment_id=experiment_id,
            plan=plan,
            slug_index=0,
            log_path=log_path,
            state="prepared"
        )

        self.mode = "experiment"

        print(f"[EXPERIMENT] {experiment_id} loaded")
        print(f"[EXPERIMENT] Plan ready")
        print(f"[EXPERIMENT] Log ready")
        print(f"[EXPERIMENT] Awaiting begin_run()")

    def _append_event(self, event_type: str, payload: dict):
        if self.context is None:
            return

        with open(self.context.log_path, "r") as f:
            log_data = json.load(f)

        log_data.setdefault("events", []).append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "event_type": event_type,
                "payload": payload,
            }
        )

        with open(self.context.log_path, "w") as f:
            json.dump(log_data, f, indent=2)

    def begin_run(self):
        if self.context is None:
            raise Exception("No experiment loaded")

        if self.context.state != "prepared":
            raise Exception(
                f"Cannot begin run while state = {self.context.state}"
            )

        self.context.state = "running"
        print(f"[EXPERIMENT] {self.context.experiment_id} now running")
        self._append_event(
            "begin_run",
            {"experiment_id": self.context.experiment_id},
        )

    def end_experiment(self):
        if self.context is None:
            print("[EXPERIMENT] No active experiment")
            return

        print(f"[EXPERIMENT] Ending {self.context.experiment_id}")

        self.context = None
        self.mode = "untracked"

    def is_experiment_active(self):
        return self.context is not None

    def get_next_slug(self):
        if self.context is None:
            return None

        slugs = self.context.plan["slugs"]

        if self.context.slug_index >= len(slugs):
            raise Exception("No slugs remaining in plan")

        slug = slugs[self.context.slug_index]
        self.context.slug_index += 1
        return slug

    def remaining_slugs(self):
        if self.context is None:
            return []

        slugs = self.context.plan["slugs"]
        return slugs[self.context.slug_index :]

    def preview(self):
        if self.context is None:
            print("[EXPERIMENT] No active experiment")
            return []

        preview_rows = []

        for index, slug in enumerate(self.context.plan["slugs"], start=1):
            reaction_plan = slug.get("reaction_plan", [])
            total_volume = sum(
                component.get("volume_uL", component.get("volume", 0.0))
                for component in reaction_plan
            )

            component_text = ", ".join(
                f"{component['module']}:{component['vial']} ({component.get('volume_uL', component.get('volume'))} uL)"
                for component in reaction_plan
            )

            row = {
                "slug_number": index,
                "slug_id": slug.get("slug_id", f"slug_{index}"),
                "num_components": len(reaction_plan),
                "total_volume_uL": total_volume,
                "components": component_text,
            }
            preview_rows.append(row)

        for row in preview_rows:
            print(
                f"{row['slug_number']}. {row['slug_id']} | "
                f"{row['num_components']} components | "
                f"{row['total_volume_uL']} uL | "
                f"{row['components']}"
            )

        return preview_rows

    def run_remaining_slugs(
        self,
        rsg,
        air_gap_between=None,
        dispense_rate=None,
        inject=True,
    ):
        if self.context is None:
            raise Exception("No experiment loaded")

        if self.context.state != "running":
            raise Exception(
                f"Experiment must be running before execution. Current state: {self.context.state}"
            )

        defaults = self.context.plan.get("global_conditions", {})
        air_gap_between = defaults.get("air_gap_between_uL", 5.0) if air_gap_between is None else air_gap_between
        dispense_rate = defaults.get("dispense_rate_mL_min", 0.5) if dispense_rate is None else dispense_rate

        results = []

        while self.context.slug_index < len(self.context.plan["slugs"]):
            slug = self.get_next_slug()
            result = rsg.create_slug(
                slug,
                air_gap_between=air_gap_between,
                dispense_rate=dispense_rate,
                inject=inject,
            )
            results.append(result)

            self._append_event(
                "slug_created",
                {
                    "slug_id": result["slug_id"],
                    "dispensed_volume_ul": result["dispensed_volume_ul"],
                    "num_components": result["num_components"],
                    "injected": result["injected"],
                },
            )

            print(
                f"[EXPERIMENT] Completed {result['slug_id']} "
                f"({result['dispensed_volume_ul']} uL)"
            )

        self._append_event(
            "all_slugs_completed",
            {"experiment_id": self.context.experiment_id},
        )

        return results

    def status(self):
        if self.context is None:
            print("Mode: untracked")
            return

        print(f"Mode: experiment")
        print(f"Experiment: {self.context.experiment_id}")
        print(f"State: {self.context.state}")
        print(f"Slug index: {self.context.slug_index}")
