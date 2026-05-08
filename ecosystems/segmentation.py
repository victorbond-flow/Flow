import time
from enum import Enum, auto
from dataclasses import dataclass

from instruments.vici.dim import DIMState
from instruments.vici.fsm import FSMState


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
        except Exception:
            print("[Segmentation] Hardware init skipped (likely simulation mode)")

    # ------------------------------------------------------------------
    # Solvent flush / conditioning
    # ------------------------------------------------------------------

    def prime_with_solvent(self, flowrate_ul_min, duration_s):
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

        self.fsm.carrier_to_dim()
        self.state.fsm = FSMState.CARRIER_TO_DIM

        self.dim.inject()
        self.state.dim = DIMState.INJECT

        self.carrier.set_flow_rate(flowrate_ul_min)
        self.carrier.start_flow()

        time.sleep(duration_s)

        self.carrier.stop_flow()

        self._set_phase(SegmentationPhase.READY)

    # ------------------------------------------------------------------
    # Gas spacer generation
    # ------------------------------------------------------------------

    def prime_gas_path(self, duration_s):
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

        self.fsm.gas_to_dim()
        self.state.fsm = FSMState.GAS_TO_DIM

        self.dim.inject()
        self.state.dim = DIMState.INJECT

        time.sleep(duration_s)

        self._set_phase(SegmentationPhase.GAS_PRIMED)

    # ------------------------------------------------------------------
    # Load reaction segment into loop
    # ------------------------------------------------------------------

    def prepare_slug(self, slug_plan, air_gap_between=5.0):
        """
        Build liquid reaction slug and load into DIM loop.
        """

        self._require_phase(SegmentationPhase.GAS_PRIMED)
        self._set_phase(SegmentationPhase.LOOP_LOADING)

        self.dim.load()
        self.state.dim = DIMState.LOAD

        result = self.rsg.build_rxn_segment(
            slug_plan=slug_plan,
            air_gap_between=air_gap_between,
        )

        self._set_phase(SegmentationPhase.LOOP_LOADED)

        return result

    # ------------------------------------------------------------------
    # Launch slug downstream
    # ------------------------------------------------------------------

    def launch_segment(self, flowrate_ul_min):
        self._require_phase(SegmentationPhase.LOOP_LOADED)

        self.fsm.carrier_to_dim()
        self.state.fsm = FSMState.CARRIER_TO_DIM

        self.dim.inject()
        self.state.dim = DIMState.INJECT

        self.carrier.set_flow_rate(flowrate_ul_min)
        self.carrier.start_flow()

        self._set_phase(SegmentationPhase.RUNNING)

        print(
            f"[Segmentation] Segment launched at "
            f"{flowrate_ul_min} µL/min"
        )

    # ------------------------------------------------------------------
    # High level slug commands
    # ------------------------------------------------------------------

    def reset_for_next_slug(self):
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
        self.fsm.gas_to_dim()
        self.state.fsm = FSMState.GAS_TO_DIM

        self.dim.inject()
        self.state.dim = DIMState.INJECT

        self._set_phase(SegmentationPhase.GAS_PRIMED)

    def create_slug(
    self,
    slug_plan,
    gas_prime_s,
    flowrate_ul_min,
    air_gap_between=5.0,
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
        )

        self.launch_segment(flowrate_ul_min=flowrate_ul_min)

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

    def stop_flow(self):
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

        self.carrier.stop_flow()

        self.fsm.carrier_to_dim()
        self.state.fsm = FSMState.CARRIER_TO_DIM

        self.dim.inject()
        self.state.dim = DIMState.INJECT

        self._set_phase(SegmentationPhase.READY)

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

    def reset(self, flowrate_ul_min, flush_time_sec):
        if self.state.phase != SegmentationPhase.ABORTED:
            raise RuntimeError(
                "Reset only allowed from ABORTED state."
            )

        self.fsm.carrier_to_dim()
        self.state.fsm = FSMState.CARRIER_TO_DIM

        self.dim.inject()
        self.state.dim = DIMState.INJECT

        self.carrier.set_flow_rate(flowrate_ul_min)
        self.carrier.start_flow()

        time.sleep(flush_time_sec)

        self.carrier.stop_flow()

        self._set_phase(SegmentationPhase.READY)

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

    def _set_phase(self, new_phase):
        print(
            f"[Segmentation] Phase: "
            f"{self.state.phase.name} -> {new_phase.name}"
        )
        self.state.phase = new_phase

