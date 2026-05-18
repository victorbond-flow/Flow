import time
from enum import Enum, auto
from dataclasses import dataclass

from instruments.vici.dim import DIMState
from instruments.vici.fsm import FSMState
from core.tracing import append_trace


class SegmentationPhase(Enum):
    READY = auto()
    GAS_PRIMED = auto()
    LOOP_LOADING = auto()
    LOOP_LOADED = auto()
    RUNNING = auto()
    ABORTED = auto()
    ERROR = auto()


@dataclass
class SegmentationState:
    dim: DIMState
    fsm: FSMState
    phase: SegmentationPhase

    def __str__(self):
        return (
            f"Segmentation phase = {self.phase.name} | "
            f"DIM = {self.dim.name} | "
            f"FSM = {self.fsm.name}"
        )

    def __repr__(self):
        return self.__str__()


class Segmentation:

    def __init__(self, dim, fsm, carrier_pump, rsg, sim_mode=False):
        self.dim = dim
        self.fsm = fsm
        self.carrier = carrier_pump
        self.rsg = rsg
        self.sim_mode = sim_mode

        if not self.sim_mode:

            # Safe baseline on startup
            try:
                self.carrier.stop_flow()
            except Exception:
                pass

        # initialise state BEFORE hardware calls (important for simulation safety)
        self.state = SegmentationState(
            dim=DIMState.INJECT,
            fsm=FSMState.CARRIER_TO_DIM,
            phase=SegmentationPhase.READY
        )

        # hardware init (optional in simulation)
        try:
            if self.fsm is not None:
                self.fsm.carrier_to_dim()
            if self.dim is not None:
                self.dim.inject()
        except Exception as exc:
            print(f"[Segmentation] Hardware init failed: {exc}")
            raise

    # ------------------------------------------------------------------
    # Solvent flush / conditioning
    # ------------------------------------------------------------------

    def prime_with_solvent(self, flowrate_ul_min, duration_s, dry_run=False, trace=None):
        """
        Flush system with solvent.
        Allowed from READY or RUNNING.
        """

        if self.state.phase not in (
            SegmentationPhase.READY,
            SegmentationPhase.RUNNING,
        ):
            raise RuntimeError(
                f"Cannot solvent prime from {self.state.phase.name}"
            )

        if dry_run:
            self.fsm.carrier_to_dim(dry_run=True, trace=trace)
        else:
            self.fsm.carrier_to_dim()
        self.state.fsm = FSMState.CARRIER_TO_DIM

        if dry_run:
            self.dim.inject(dry_run=True, trace=trace)
        else:
            self.dim.inject()
        self.state.dim = DIMState.INJECT

        if dry_run:
            self.carrier.set_flow_rate(flowrate_ul_min, dry_run=True, trace=trace)
            self.carrier.start_flow(dry_run=True, trace=trace)
        else:
            self.carrier.set_flow_rate(flowrate_ul_min)
            self.carrier.start_flow()

        if not dry_run:
            time.sleep(duration_s)

        if dry_run:
            self.carrier.stop_flow(dry_run=True, trace=trace)
        else:
            self.carrier.stop_flow()

        self._set_phase(SegmentationPhase.READY, trace=trace)

    # ------------------------------------------------------------------
    # Gas spacer generation
    # ------------------------------------------------------------------

    def prime_gas_path(self, duration_s, dry_run=False, trace=None):
        """
        Establish gas spacer geometry for next slug.
        Allowed from READY or RUNNING.
        """

        if self.state.phase not in (
            SegmentationPhase.READY,
            SegmentationPhase.RUNNING,
        ):
            raise RuntimeError(
                f"Cannot prime gas path from {self.state.phase.name}"
            )

        if dry_run:
            self.fsm.gas_to_dim(dry_run=True, trace=trace)
        else:
            self.fsm.gas_to_dim()
        self.state.fsm = FSMState.GAS_TO_DIM

        if dry_run:
            self.dim.inject(dry_run=True, trace=trace)
        else:
            self.dim.inject()
        self.state.dim = DIMState.INJECT

        append_trace(
            trace,
            step="segmentation",
            action="prime_gas_path",
            notes=f"duration_s={duration_s}",
        )

        if not dry_run:
            time.sleep(duration_s)

        self._set_phase(SegmentationPhase.GAS_PRIMED, trace=trace)

    # ------------------------------------------------------------------
    # Load reaction segment into loop
    # ------------------------------------------------------------------

    def prepare_slug(
        self,
        slug_plan,
        air_gap_between=5.0,
        dispense_rate=0.5,
        withdraw_rate=None,
        dry_run=False,
        trace=None,
    ):
        """
        Build liquid reaction slug and load into DIM loop.
        """

        self._require_phase(SegmentationPhase.GAS_PRIMED)
        self._set_phase(SegmentationPhase.LOOP_LOADING, trace=trace)

        if dry_run:
            self.dim.load(dry_run=True, trace=trace)
        else:
            self.dim.load()
        self.state.dim = DIMState.LOAD

        result = self.rsg.build_rxn_segment(
            slug_plan=slug_plan,
            air_gap_between=air_gap_between,
            withdraw_rate=withdraw_rate,
            dispense_rate=dispense_rate,
            dry_run=dry_run,
            trace=trace,
        )

        self._set_phase(SegmentationPhase.LOOP_LOADED, trace=trace)

        return result

    # ------------------------------------------------------------------
    # Launch slug downstream
    # ------------------------------------------------------------------

    def launch_segment(self, flowrate_ul_min, dry_run=False, trace=None):
        self._require_phase(SegmentationPhase.LOOP_LOADED)

        if dry_run:
            self.fsm.carrier_to_dim(dry_run=True, trace=trace)
        else:
            self.fsm.carrier_to_dim()
        self.state.fsm = FSMState.CARRIER_TO_DIM

        if dry_run:
            self.dim.inject(dry_run=True, trace=trace)
        else:
            self.dim.inject()
        self.state.dim = DIMState.INJECT

        if dry_run:
            self.carrier.set_flow_rate(flowrate_ul_min, dry_run=True, trace=trace)
            self.carrier.start_flow(dry_run=True, trace=trace)
        else:
            self.carrier.set_flow_rate(flowrate_ul_min)
            self.carrier.start_flow()

        self._set_phase(SegmentationPhase.RUNNING, trace=trace)

        if trace is None:
            print(
                f"[Segmentation] Segment launched at "
                f"{flowrate_ul_min} µL/min"
            )

    # ------------------------------------------------------------------
    # High level slug commands
    # ------------------------------------------------------------------

    def reset_for_next_slug(self, dry_run=False, trace=None):
        """
        Explicit transition:
        RUNNING → GAS_PRIMED

        Prepares system for next slug cycle.
        """
        if self.state.phase != SegmentationPhase.RUNNING:
            raise RuntimeError(
                f"Can only reset from RUNNING, currently {self.state.phase.name}"
            )

        # Re-establish gas spacer geometry
        if dry_run:
            self.fsm.gas_to_dim(dry_run=True, trace=trace)
        else:
            self.fsm.gas_to_dim()
        self.state.fsm = FSMState.GAS_TO_DIM

        if dry_run:
            self.dim.inject(dry_run=True, trace=trace)
        else:
            self.dim.inject()
        self.state.dim = DIMState.INJECT

        self._set_phase(SegmentationPhase.GAS_PRIMED, trace=trace)

    def create_slug(
    self,
    slug_plan,
    gas_prime_s,
    flowrate_ul_min,
    air_gap_between=5.0,
    dispense_rate = 0.5,
    withdraw_rate = None,
    dry_run=False,
    trace=None,
):
        """
        Executes a single slug cycle.

        Assumes system is already in GAS_PRIMED state.
        """

        # ------------------------------------------------------------
        # SAFETY GUARD (CRITICAL FOR PHYSICAL CORRECTNESS)
        # ------------------------------------------------------------
        if self.state.phase != SegmentationPhase.GAS_PRIMED:
            raise RuntimeError(
                f"create_slug expects GAS_PRIMED, got {self.state.phase.name}"
            )

        slug_id = slug_plan.get("slug_id", "untracked-slug")

        result = self.prepare_slug(
            slug_plan=slug_plan,
            air_gap_between=air_gap_between,
            withdraw_rate=withdraw_rate,
            dispense_rate=dispense_rate,
            dry_run=dry_run,
            trace=trace,
        )

        self.launch_segment(
            flowrate_ul_min=flowrate_ul_min,
            dry_run=dry_run,
            trace=trace,
        )

        return {
            "slug_id": slug_id,
            "dispensed_volume_ul": result.get(
                "dispensed_volume_ul",
                result.get("total_volume_ul", 0.0),
            ),
            "num_components": result.get("num_components", 0),
            "launched": True,
        }

    # ------------------------------------------------------------------
    # Stop campaign flow manually
    # ------------------------------------------------------------------

    def stop_flow(self, dry_run=False, trace=None):
        """
        Stop carrier flow and return to READY state.
        """

        if self.state.phase not in (
            SegmentationPhase.RUNNING,
            SegmentationPhase.READY,
        ):
            raise RuntimeError(
                f"Cannot stop flow from {self.state.phase.name}"
            )

        if dry_run:
            self.carrier.stop_flow(dry_run=True, trace=trace)
        else:
            self.carrier.stop_flow()

        if dry_run:
            self.fsm.carrier_to_dim(dry_run=True, trace=trace)
        else:
            self.fsm.carrier_to_dim()
        self.state.fsm = FSMState.CARRIER_TO_DIM

        if dry_run:
            self.dim.inject(dry_run=True, trace=trace)
        else:
            self.dim.inject()
        self.state.dim = DIMState.INJECT

        self._set_phase(SegmentationPhase.READY, trace=trace)

    # ------------------------------------------------------------------
    # Abort
    # ------------------------------------------------------------------

    def abort(self):
        if self.state.phase == SegmentationPhase.ABORTED:
            print("[Segmentation] Already aborted.")
            return

        print(
            f"[Segmentation] ABORT triggered from "
            f"{self.state.phase.name}"
        )

        try:
            self.carrier.stop_flow()
        except Exception:
            pass

        try:
            self.fsm.carrier_to_dim()
            self.state.fsm = FSMState.CARRIER_TO_DIM
        except Exception:
            pass

        try:
            self.dim.inject()
            self.state.dim = DIMState.INJECT
        except Exception:
            pass

        self._set_phase(SegmentationPhase.ABORTED)

    # ------------------------------------------------------------------
    # Reset after abort
    # ------------------------------------------------------------------

    def reset(self, flowrate_ul_min, flush_time_sec, dry_run=False, trace=None):
        if self.state.phase != SegmentationPhase.ABORTED:
            raise RuntimeError(
                "Reset only allowed from ABORTED state."
            )

        if dry_run:
            self.fsm.carrier_to_dim(dry_run=True, trace=trace)
        else:
            self.fsm.carrier_to_dim()
        self.state.fsm = FSMState.CARRIER_TO_DIM

        if dry_run:
            self.dim.inject(dry_run=True, trace=trace)
        else:
            self.dim.inject()
        self.state.dim = DIMState.INJECT

        if dry_run:
            self.carrier.set_flow_rate(flowrate_ul_min, dry_run=True, trace=trace)
            self.carrier.start_flow(dry_run=True, trace=trace)
        else:
            self.carrier.set_flow_rate(flowrate_ul_min)
            self.carrier.start_flow()

        if not dry_run:
            time.sleep(flush_time_sec)

        if dry_run:
            self.carrier.stop_flow(dry_run=True, trace=trace)
        else:
            self.carrier.stop_flow()

        self._set_phase(SegmentationPhase.READY, trace=trace)

        if trace is None:
            print("[Segmentation] Reset complete.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_phase(self, required_phase):
        if self.state.phase != required_phase:
            raise RuntimeError(
                f"Required {required_phase.name}, "
                f"current = {self.state.phase.name}"
            )

    def _set_phase(self, new_phase, trace=None):
        if trace is None:
            print(
                f"[Segmentation] Phase: "
                f"{self.state.phase.name} -> {new_phase.name}"
            )
        self.state.phase = new_phase

