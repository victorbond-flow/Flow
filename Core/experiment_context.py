from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from datetime import datetime
import json

from Core.experiment_validator import ExperimentValidator


@dataclass
class ExperimentContext:
    experiment_id: str
    plan: dict
    slug_index: int
    log_path: Path
    state: str   # prepared / armed / running / completed / failed / aborted


class ExperimentManager:
    def __init__(self):
        self.mode = "untracked"
        self.context: Optional[ExperimentContext] = None

        self.repo_root = Path(__file__).resolve().parent.parent
        self.experiments_root = self.repo_root / "Experiments"

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

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
                json.dump(
                    {
                        "experiment_id": experiment_id,
                        "events": []
                    },
                    f,
                    indent=2
                )
    
        self.context = ExperimentContext(
            experiment_id=experiment_id,
            plan=plan,
            slug_index=0,
            log_path=log_path,
            state="prepared"
        )
    
        self.mode = "experiment"
    
        print(f"[EXPERIMENT] {experiment_id} loaded")
        print("[EXPERIMENT] Plan ready")
        print("[EXPERIMENT] Log ready")
        print("[EXPERIMENT] State = prepared")
        print("[EXPERIMENT] Awaiting arm_experiment()")
    
        self._append_event(
            "experiment_loaded",
            {"experiment_id": experiment_id},
        )

    # ------------------------------------------------------------------
    # Arm
    # ------------------------------------------------------------------

    def arm_experiment(self):
        if self.context is None:
            raise Exception("No experiment loaded")
    
        if self.context.state != "prepared":
            raise Exception(
                f"Cannot arm experiment while state = {self.context.state}"
            )

        self._validate_loaded_plan()

        self.context.state = "armed"
    
        print(f"[EXPERIMENT] {self.context.experiment_id} armed")
        print("[EXPERIMENT] Awaiting execute_experiment()")
    
        self._append_event(
            "experiment_armed",
            {"experiment_id": self.context.experiment_id},
        )

    # ------------------------------------------------------------------
    # Preview the plan
    # ------------------------------------------------------------------

    def preview(self):
        """
        Prints a human-readable overview of the loaded experiment plan.
        Safe inspection tool — does not mutate state.
        """
    
        if self.context is None:
            print("[EXPERIMENT] No active experiment")
            return []
    
        slugs = self.context.plan.get("slugs", [])
        preview_rows = []
    
        print("\n[EXPERIMENT PREVIEW]")
        print("-" * 60)
    
        for index, slug in enumerate(slugs, start=1):
    
            reaction_plan = slug.get("reaction_plan", [])
    
            # robust volume extraction (handles uL / volume mismatch)
            total_volume = sum(
                comp.get("volume_uL", comp.get("volume", 0.0))
                for comp in reaction_plan
            )
    
            components = ", ".join(
                f"{comp.get('module')}:{comp.get('vial')} "
                f"({comp.get('volume_uL', comp.get('volume'))} uL)"
                for comp in reaction_plan
            )
    
            row = {
                "slug_number": index,
                "slug_id": slug.get("slug_id", f"slug_{index}"),
                "num_components": len(reaction_plan),
                "total_volume_uL": total_volume,
                "components": components,
            }
    
            preview_rows.append(row)
    
            print(
                f"{row['slug_number']}. {row['slug_id']} | "
                f"{row['num_components']} components | "
                f"{row['total_volume_uL']} uL\n"
                f"   {row['components']}"
            )
    
        print("-" * 60)
        print(f"[EXPERIMENT] {len(slugs)} slugs total\n")
    
        return preview_rows

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute_experiment(
        self,
        seg,
        gas_prime_s=None,
        flowrate_ul_min=None,
        air_gap_between=None,
    ):
        if self.context is None:
            raise Exception("No experiment loaded")
    
        if self.context.state != "armed":
            raise Exception(
                f"Experiment must be armed. Current state: {self.context.state}"
            )

        self._validate_loaded_plan()
    
        self.context.state = "running"

        results = []

        try:
            defaults = self.context.plan.get("global_conditions", {})

            if gas_prime_s is None:
                gas_prime_s = defaults["gas_prime_s"]

            if flowrate_ul_min is None:
                flowrate_ul_min = defaults["flowrate_ul_min"]

            if air_gap_between is None:
                air_gap_between = defaults.get("air_gap_between_uL", 5.0)

            slugs = self.context.plan["slugs"]

            print(f"[EXPERIMENT] Executing {self.context.experiment_id}")

            for i in range(self.context.slug_index, len(slugs)):

                slug = slugs[i]
                slug_id = slug.get("slug_id", f"slug_{i + 1}")

                self._append_event(
                    "slug_started",
                    {
                        "slug_index": i,
                        "slug_number": i + 1,
                        "slug_id": slug_id,
                    },
                )

                try:
                    # First slug vs subsequent slugs
                    if i == 0:
                        seg.prime_gas_path(duration_s=gas_prime_s)
                    else:
                        seg.reset_for_next_slug()

                    result = seg.create_slug(
                        slug_plan=slug,
                        gas_prime_s=gas_prime_s,
                        flowrate_ul_min=flowrate_ul_min,
                        air_gap_between=air_gap_between,
                    )
                except Exception as exc:
                    self._append_event(
                        "slug_failed",
                        {
                            "slug_index": i,
                            "slug_number": i + 1,
                            "slug_id": slug_id,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                    raise

                results.append(result)

                self.context.slug_index += 1

                self._append_event(
                    "slug_created",
                    {
                        "slug_index": i,
                        "slug_number": i + 1,
                        "slug_id": result["slug_id"],
                        "dispensed_volume_ul": result["dispensed_volume_ul"],
                        "num_components": result["num_components"],
                        "launched": result["launched"],
                    },
                )

                print(
                    f"[EXPERIMENT] Completed {result['slug_id']} "
                    f"({result['dispensed_volume_ul']} uL)"
                )

            self.context.state = "completed"

            self._append_event(
                "experiment_completed",
                {"experiment_id": self.context.experiment_id},
            )

            print(f"[EXPERIMENT] {self.context.experiment_id} completed")

            return results

        except KeyboardInterrupt:
            self.context.state = "aborted"
            self._append_event(
                "user_aborted",
                {
                    "experiment_id": self.context.experiment_id,
                    "slug_index": self.context.slug_index,
                },
            )
            self._abort_seg(seg)
            print(f"[EXPERIMENT] {self.context.experiment_id} aborted by user")
            raise

        except Exception as exc:
            self.context.state = "failed"
            self._append_event(
                "experiment_failed",
                {
                    "experiment_id": self.context.experiment_id,
                    "slug_index": self.context.slug_index,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            self._abort_seg(seg)
            print(f"[EXPERIMENT] {self.context.experiment_id} failed: {exc}")
            raise

    # ------------------------------------------------------------------
    # Slug handling
    # ------------------------------------------------------------------

    def get_next_slug(self):
        slugs = self.context.plan["slugs"]

        if self.context.slug_index >= len(slugs):
            raise Exception("No slugs remaining")

        slug = slugs[self.context.slug_index]
        self.context.slug_index += 1
        return slug

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

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

    def _validate_loaded_plan(self):
        if self.context is None:
            raise Exception("No experiment loaded")

        result = ExperimentValidator().validate_plan(self.context.plan)
        if result["passed"]:
            return

        message = "Invalid experiment plan:\n" + "\n".join(
            f"- {error}" for error in result["errors"]
        )
        raise ValueError(message)

    def _abort_seg(self, seg):
        abort = getattr(seg, "abort", None)
        if abort is None:
            return

        try:
            abort()
        except Exception as exc:
            self._append_event(
                "abort_failed",
                {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self):
        if self.context is None:
            print("Mode: untracked")
            return

        print(f"Mode: experiment")
        print(f"Experiment: {self.context.experiment_id}")
        print(f"State: {self.context.state}")
        print(f"Slug index: {self.context.slug_index}")
