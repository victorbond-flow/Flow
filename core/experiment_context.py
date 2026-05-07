from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from datetime import datetime
import json
import time

from core.experiment_validator import ExperimentValidator


@dataclass
class ExperimentContext:
    experiment_id: str
    plan: dict
    slug_index: int
    log_path: Path
    state: str   # prepared / armed / running / completed / failed / aborted


class ExperimentManager:
    SYSTEM_UNKNOWN = "UNKNOWN"
    REACTOR_READY = "REACTOR_READY"
    RSG_READY = "RSG_READY"
    PLATFORM_READY = "PLATFORM_READY"
    SYSTEM_RUNNING = "RUNNING"
    SYSTEM_FAULT = "FAULT"

    def __init__(self):
        self.mode = "untracked"
        self.context: Optional[ExperimentContext] = None
        self.system_state = self.SYSTEM_UNKNOWN

        # --- Platform readiness tracking ---
        self.reactor_state = self.SYSTEM_UNKNOWN
        self.rsg_state = self.SYSTEM_UNKNOWN
        self.platform_state = self.SYSTEM_UNKNOWN

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
        
        # NEW: ensure we always start from a clean platform state
        self._reset_platform_states()
        self.system_state = self.SYSTEM_UNKNOWN
    
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
    # System readiness
    # ------------------------------------------------------------------

    def precondition_reactor(
    self,
    seg,
    carrier_flowrate_ul_min=1000,
    stabilisation_time_s=20,
):
        """
        Sets DIM/FSM + starts carrier flow + stabilises system.
        """
    
        fsm = seg.fsm
        dim = seg.dim
        carrier = seg.carrier
    
        print("[REACTOR] Setting valve positions")
    
        fsm.carrier_to_dim()
        dim.inject()
    
        carrier.set_flow_rate(carrier_flowrate_ul_min)
        carrier.start_flow()
    
        print("[REACTOR] Stabilising...")
    
        time.sleep(stabilisation_time_s)
    
        self.reactor_state = self.REACTOR_READY
        self._update_platform_state()
    
        self._append_event(
            "reactor_ready",
            {
                "flowrate_ul_min": carrier_flowrate_ul_min,
                "stabilisation_time_s": stabilisation_time_s,
            },
        )
    
        print("[SYSTEM] Reactor READY")
    
    def prepare_rsg(
    self,
    seg,
    air_gap: float = 20.0,
    rate_wdr: float = 0.25,
):
        """
        Prepares syringe pump fluid stack + autosampler system for slug creation.
        """
    
        rsg = getattr(seg, "rsg", None)
        if rsg is None or not hasattr(rsg, "initialise"):
            raise RuntimeError("RSG not available")
    
        print("[RSG] Initialising")
    
        try:
            rsg.initialise(air_gap=air_gap, rate_wdr=rate_wdr)
        except Exception as exc:
            self.rsg_state = self.SYSTEM_UNKNOWN
            self.platform_state = self.SYSTEM_UNKNOWN
            self.system_state = self.SYSTEM_FAULT
            self._update_platform_state()
            raise
    
        self.rsg_state = self.RSG_READY
        self._update_platform_state()
    
        self._append_event(
            "rsg_ready",
            {
                "air_gap_uL": air_gap,
                "rate_wdr_mL_min": rate_wdr,
            },
        )
    
        print("[SYSTEM] RSG READY")

    # ------------------------------------------------------------------
    # Preview Execution (full trace)
    # ------------------------------------------------------------------
    def preview_execution(
    self,
    seg,
    gas_prime_s=None,
    flowrate_ul_min=None,
    air_gap_between=None,
    wash_policy="none",
):
        """
        Dry-run execution trace of the experiment.
    
        Returns a list of steps representing EXACT execution order.
        Does NOT send commands to hardware.
        """
    
        if self.context is None:
            raise Exception("No experiment loaded")
    
        defaults = self.context.plan.get("global_conditions", {})
    
        if gas_prime_s is None:
            gas_prime_s = defaults["gas_prime_s"]
    
        if flowrate_ul_min is None:
            flowrate_ul_min = defaults["flowrate_ul_min"]
    
        if air_gap_between is None:
            air_gap_between = defaults.get("air_gap_between_uL", 5.0)
    
        # ⚠️ MUST match RSG behaviour
        POST_AIR_GAP = 5.0
    
        slugs = self.context.plan["slugs"]
    
        trace = []
    
        for i, slug in enumerate(slugs):
            slug_id = slug.get("slug_id", f"slug_{i+1}")
    
            trace.append(f"\n--- SLUG {i+1}: {slug_id} ---")
    
            if i == 0:
                trace.append(f"seg.prime_gas_path({gas_prime_s}s)")
            else:
                trace.append("seg.reset_for_next_slug()")
    
            trace.append("seg.create_slug(...)")
            trace.append("  → RSG.build_rxn_segment()")
    
            # --------------------------------------------------
            # Handle both possible formats
            # --------------------------------------------------
            components = (
                slug.get("reaction_plan")
                or slug.get("components")
                or []
            )
    
            liquid_volume = 0.0
    
            for comp in components:
                vol = comp["volume_uL"]
                liquid_volume += vol
    
                trace.append(
                    f"    → pickup {vol} uL "
                    f"from {comp['module']} vial {comp['vial']}"
                )
    
            n_components = len(components)
    
            between_gap_total = (
                air_gap_between * (n_components - 1)
                if n_components > 1 else 0.0
            )
    
            if n_components > 1:
                trace.append(
                    f"    → internal air gaps: {air_gap_between} uL × {n_components - 1}"
                )
    
            trace.append(f"    → post-pickup air gap ({POST_AIR_GAP} uL)")
    
            total_volume = liquid_volume + between_gap_total + POST_AIR_GAP
    
            # --------------------------------------------------
            # CRITICAL LINE (this is what you wanted)
            # --------------------------------------------------
            trace.append(
                f"  → dispense {total_volume:.1f} uL to DIM "
                f"({liquid_volume:.1f} liquid + "
                f"{between_gap_total:.1f} between + "
                f"{POST_AIR_GAP:.1f} post-air)"
            )
    
            trace.append("  → switch DIM to inject")
            trace.append(f"  → start carrier flow ({flowrate_ul_min} uL/min)")
    
            if wash_policy == "needle":
                trace.append("  → RSG.needle_wash()")
    
        return trace
    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute_experiment(
        self,
        seg,
        gas_prime_s=None,
        flowrate_ul_min=None,
        air_gap_between=None,
        wash_policy: str = "needle_only",
    ):
        if self.context is None:
            raise Exception("No experiment loaded")
    
        if self.context.state != "armed":
            raise Exception(
                f"Experiment must be armed. Current state: {self.context.state}"
            )
    
        if self.platform_state != self.PLATFORM_READY:
            raise RuntimeError(
                "Platform not ready. "
                f"Reactor={self.reactor_state}, RSG={self.rsg_state}"
            )
    
        self._validate_loaded_plan()
    
        self.context.state = "running"
        self.system_state = self.SYSTEM_RUNNING
    
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
    
                        # -----------------------------
                        # WASH POLICY (NEW)
                        # -----------------------------
                        if wash_policy == "needle_only":
                            seg.rsg.needle_wash()
    
                        elif wash_policy == "full":
                            seg.rsg.between_slug_wash()
    
                        elif wash_policy == "none":
                            pass
    
                        else:
                            raise ValueError(f"Unknown wash_policy: {wash_policy}")
    
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
            self.system_state = self.SYSTEM_UNKNOWN
    
            self._append_event(
                "experiment_completed",
                {"experiment_id": self.context.experiment_id},
            )
    
            print(f"[EXPERIMENT] {self.context.experiment_id} completed")
    
            return results
    
        except KeyboardInterrupt:
            self.context.state = "aborted"
            self.system_state = self.SYSTEM_FAULT
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
            self.system_state = self.SYSTEM_FAULT
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
        print(f"System state: {self.system_state}")
        print(f"Reactor state: {self.reactor_state}")
        print(f"RSG state: {self.rsg_state}")
        print(f"Platform state: {self.platform_state}")
        print(f"Slug index: {self.context.slug_index}")

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _update_platform_state(self):
        if (
            self.reactor_state == self.REACTOR_READY
            and self.rsg_state == self.RSG_READY
        ):
            self.platform_state = self.PLATFORM_READY
        else:
            self.platform_state = self.SYSTEM_UNKNOWN

    def _reset_platform_states(self):
        """
        Hard reset all platform readiness flags.
        Called whenever a new experiment is loaded.
        """
        self.reactor_state = self.SYSTEM_UNKNOWN
        self.rsg_state = self.SYSTEM_UNKNOWN
        self.platform_state = self.SYSTEM_UNKNOWN
    
