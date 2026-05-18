from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from datetime import datetime
import copy
import json
import time

from core.experiment_validator import ExperimentValidator
from core.tracing import append_trace


@dataclass
class ExperimentContext:
    experiment_id: str
    plan: dict
    slug_index: int
    log_path: Path
    state: str   # prepared / armed / running / completed / failed / aborted
    system_snapshot: Optional[dict] = None


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
        self.trace = []

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
            state="prepared",
            system_snapshot=None,
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

        self.context.system_snapshot = self._capture_experiment_snapshot(
            seg,
            air_gap=air_gap,
            rate_wdr=rate_wdr,
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
        dry_run=True,
    ):

        if self.context is None:
            raise Exception("No experiment loaded")

        self.trace = []

        self.execute_experiment(
            seg=seg,
            gas_prime_s=gas_prime_s,
            flowrate_ul_min=flowrate_ul_min,
            air_gap_between=air_gap_between,
            wash_policy=wash_policy,
            dry_run=dry_run,
            trace=self.trace,
        )

        return self.trace
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
        dry_run: bool = False,
        trace=None,
    ):
        if self.context is None:
            raise Exception("No experiment loaded")

        if not dry_run and self.context.state != "armed":
            raise Exception(
                f"Experiment must be armed. Current state: {self.context.state}"
            )

        if not dry_run and self.platform_state != self.PLATFORM_READY:
            raise RuntimeError(
                "Platform not ready. "
                f"Reactor={self.reactor_state}, RSG={self.rsg_state}"
            )

        self._validate_loaded_plan()

        self.context.state = "running"
        self.system_state = self.SYSTEM_RUNNING

        if dry_run:
            append_trace(
                trace,
                step="experiment",
                action="start",
                notes=self.context.experiment_id,
            )

        results = []

        try:
            defaults = self.context.plan.get("global_conditions", {})

            # -------------------------
            # FIX: wash config (FLAT, simple, no nesting assumptions)
            # -------------------------
            needle_wash_volume_ul = defaults.get("needle_wash_volume_ul", 50.0)
            between_slug_wash_volume_ul = defaults.get("between_slug_wash_volume_ul", 100.0)

            dispense_rate_ml_min = defaults.get("dispense_rate_ml_min", 0.5)
            withdraw_rate_ml_min = defaults.get("withdraw_rate_ml_min", None)

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

                if dry_run:
                    append_trace(trace, step=f"slug_{i + 1}", action="start", notes=slug_id)
                else:
                    self._append_event(
                        "slug_started",
                        {
                            "slug_index": i,
                            "slug_number": i + 1,
                            "slug_id": slug_id,
                        },
                    )

                try:
                    # -------------------------
                    # FIRST SLUG vs NEXT SLUGS
                    # -------------------------
                    if i == 0:
                        if dry_run:
                            seg.prime_gas_path(
                                duration_s=gas_prime_s,
                                dry_run=True,
                                trace=trace,
                            )
                        else:
                            seg.prime_gas_path(duration_s=gas_prime_s)

                    else:
                        if dry_run:
                            seg.reset_for_next_slug(dry_run=True, trace=trace)
                        else:
                            seg.reset_for_next_slug()

                        # -------------------------
                        # WASH POLICY (FIXED)
                        # -------------------------
                        if wash_policy == "needle_only":
                            if dry_run:
                                seg.rsg.needle_wash(
                                    wash_solvent_volume=needle_wash_volume_ul,
                                    dry_run=True,
                                    trace=trace,
                                )
                            else:
                                seg.rsg.needle_wash(
                                    wash_solvent_volume=needle_wash_volume_ul,
                                )

                        elif wash_policy == "full":
                            if dry_run:
                                seg.rsg.between_slug_wash(
                                    wash_solvent_volume=between_slug_wash_volume_ul,
                                    dry_run=True,
                                    trace=trace,
                                )
                            else:
                                seg.rsg.between_slug_wash(
                                    wash_solvent_volume=between_slug_wash_volume_ul,
                                )

                        elif wash_policy == "none":
                            pass

                        else:
                            raise ValueError(f"Unknown wash_policy: {wash_policy}")

                    # -------------------------
                    # SLUG CREATION
                    # -------------------------

                    print("[EXECUTION ENTRY PLAN TYPE]", type(self.context.plan))

                    if hasattr(self.context.plan, "head"):
                        print("[EXECUTION ENTRY DF SHAPE]", self.context.plan.shape)
                        print("[EXECUTION ENTRY COLUMNS]", self.context.plan.columns.tolist())
                    
                    if dry_run:
                        result = seg.create_slug(
                            slug_plan=slug,
                            gas_prime_s=gas_prime_s,
                            flowrate_ul_min=flowrate_ul_min,
                            air_gap_between=air_gap_between,
                            dispense_rate=dispense_rate_ml_min,
                            withdraw_rate=withdraw_rate_ml_min,
                            dry_run=True,
                            trace=trace,
                        )
                    else:
                        result = seg.create_slug(
                            slug_plan=slug,
                            gas_prime_s=gas_prime_s,
                            flowrate_ul_min=flowrate_ul_min,
                            air_gap_between=air_gap_between,
                            dispense_rate=dispense_rate_ml_min,
                            withdraw_rate=withdraw_rate_ml_min,
                        )

                except Exception as exc:
                    if not dry_run:
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

                if dry_run:
                    append_trace(
                        trace,
                        step=f"slug_{i + 1}",
                        action="complete",
                        volume_uL=result["dispensed_volume_ul"],
                        notes=result["slug_id"],
                    )
                else:
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

            if dry_run:
                append_trace(
                    trace,
                    step="experiment",
                    action="complete",
                    notes=self.context.experiment_id,
                )
            else:
                self._append_event(
                    "experiment_completed",
                    {"experiment_id": self.context.experiment_id},
                )

            print(f"[EXPERIMENT] {self.context.experiment_id} completed")
            return results

        except KeyboardInterrupt:
            self.context.state = "aborted"
            self.system_state = self.SYSTEM_FAULT
            if not dry_run:
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
            if not dry_run:
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
    # Experiment snapshot
    # ------------------------------------------------------------------

    def _capture_experiment_snapshot(self, seg, air_gap: float, rate_wdr: float):
        """
        Store a frozen diagnostic record of state after prepare_rsg.
        The snapshot lives with ExperimentContext because it is experiment-scoped
        and should not be shared by reusable hardware/controller instances.
        It is for debugging and inspection only; preview_execution must run
        from the actual live Segmentation/RSG object state, never this snapshot.
        """
        rsg = getattr(seg, "rsg", None)
        probe = getattr(rsg, "probe", None)
        dim = getattr(seg, "dim", None)
        fsm = getattr(seg, "fsm", None)
        carrier = getattr(seg, "carrier", None)
        seg_state = getattr(seg, "state", None)
        seg_phase = getattr(seg_state, "phase", None)

        snapshot = {
            "experiment_id": self.context.experiment_id,
            "captured_after": "prepare_rsg",
            "probe": {
                "known": getattr(probe, "known", None),
                "contents": copy.deepcopy(getattr(probe, "contents", [])),
            },
            "dim": {
                "state": getattr(getattr(dim, "state", None), "name", None),
                "valve_position": self._dim_valve_position(
                    getattr(dim, "state", None)
                ),
            },
            "fsm": {
                "state": getattr(getattr(fsm, "state", None), "name", None),
                "valve_position": self._fsm_valve_position(
                    getattr(fsm, "state", None)
                ),
            },
            "segmentation": {
                "phase": getattr(seg_phase, "name", None),
            },
            "rsg": {
                "state": getattr(getattr(rsg, "state", None), "name", None),
                "initial_air_gap_uL": float(air_gap),
                "initial_air_gap_rate_mL_min": float(rate_wdr),
            },
            "carrier_pump": {
                "flow_rate_ul_min": getattr(carrier, "flow_rate_ul_min", None),
                "running": getattr(carrier, "is_running", None),
            },
        }

        self._validate_experiment_snapshot(snapshot)
        return copy.deepcopy(snapshot)

    def _validate_experiment_snapshot(self, snapshot=None):
        snapshot = snapshot or getattr(self.context, "system_snapshot", None)

        if snapshot is None:
            raise RuntimeError(
                "No experiment snapshot found. Run manager.prepare_rsg(...) "
                "before validating the experiment snapshot."
            )

        if snapshot.get("captured_after") != "prepare_rsg":
            raise RuntimeError(
                "Invalid experiment snapshot: expected state captured after "
                "prepare_rsg()."
            )

        probe = snapshot.get("probe", {})
        contents = probe.get("contents")

        if probe.get("known") is False:
            raise RuntimeError("Invalid experiment snapshot: probe state is unknown.")

        if not isinstance(contents, list) or not contents:
            raise RuntimeError(
                "Invalid experiment snapshot: probe contents are missing."
            )

        finite_air_segments = []

        for index, segment in enumerate(contents):
            if not isinstance(segment, dict):
                raise RuntimeError(
                    f"Invalid experiment snapshot: probe segment {index} "
                    "is not a dict."
                )

            fluid_type = segment.get("type")
            if fluid_type is None:
                raise RuntimeError(
                    f"Invalid experiment snapshot: probe segment {index} "
                    "is missing type."
                )

            if "volume_ul" not in segment:
                raise RuntimeError(
                    f"Invalid experiment snapshot: probe segment {index} "
                    "is missing volume_ul."
                )

            is_infinite = bool(segment.get("is_infinite", False))
            volume = segment["volume_ul"]

            if is_infinite and index != 0:
                raise RuntimeError(
                    "Invalid experiment snapshot: infinite reservoir segment "
                    "must be at the bottom of the probe stack."
                )

            if not is_infinite and volume <= 0:
                raise RuntimeError(
                    f"Invalid experiment snapshot: probe segment {index} "
                    f"has non-positive volume {volume}."
                )

            if fluid_type == "air" and not is_infinite:
                finite_air_segments.append(segment)

        if not finite_air_segments:
            raise RuntimeError(
                "Invalid experiment snapshot: missing prepared air segment in "
                "probe stack. Run manager.prepare_rsg(...) successfully before "
                "snapshot validation."
            )

        required_state_fields = (
            ("dim", "state"),
            ("fsm", "state"),
            ("segmentation", "phase"),
            ("rsg", "state"),
        )
        for section, field in required_state_fields:
            if not snapshot.get(section, {}).get(field):
                raise RuntimeError(
                    f"Invalid experiment snapshot: missing {section}.{field}."
                )

        return True

    @staticmethod
    def _dim_valve_position(state):
        state_name = getattr(state, "name", None)
        if state_name == "INJECT":
            return "A"
        if state_name == "LOAD":
            return "B"
        return None

    @staticmethod
    def _fsm_valve_position(state):
        state_name = getattr(state, "name", None)
        if state_name == "GAS_TO_DIM":
            return "A"
        if state_name == "CARRIER_TO_DIM":
            return "B"
        return None

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
    
