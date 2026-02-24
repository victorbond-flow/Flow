import time
from enum import Enum, auto
from dataclasses import dataclass

from Instruments.GX_271.dim import DIM, DIMState
from Instruments.Runze_valves.Runze62Valve import Runze62Valve, RunzeState

class SegmentationPhase(Enum):
    IDLE = auto()
    GAS_PRIMED = auto()
    LOOP_LOADING = auto()
    LOOP_LOADED = auto()
    FLOWING = auto()
    ABORTED = auto()
    ERROR = auto()

@dataclass
class SegmentationState:
    dim: DIMState
    runze: RunzeState
    phase: SegmentationPhase

    def __str__(self):
        return (
            f"Segmentation phase = {self.phase.name} | "
            f"DIM = {self.dim.name} | "
            f"Runze = {self.runze.name}"
        )

    def __repr__(self):
        return self.__str__()
    

class Segmentation:

    def __init__(self, dim, runze, carrier_pump, rsg):
        """
        Coordinates segmented flow operation across valves, carrier pump,
        and reaction preparation logic.

        Enforces a strict state progression to ensure that priming,
        loading, and flow launch occur in a physically valid order.

        Assumes:
        - All hardware is already instantiated and connected
        - RSG is already configured
        """
        self.dim = dim
        self.runze = runze
        self.carrier = carrier_pump
        self.rsg = rsg

        # Force hardware into safe baseline state
        try:
            self.carrier.stop_flow()
        except Exception:
            pass # Pump may be stopped already

        # Set valve positions at startup
        try:
            self.runze.carrier_to_dim()
            self.dim.inject()
        except Exception as e:
            raise RuntimeError("Failed to initialise segmentation hardware") from e

        # Now update internal state
        self.state = SegmentationState(
            dim=DIMState.INJECT,
            runze=RunzeState.CARRIER_TO_DIM,
            phase=SegmentationPhase.IDLE
        )

    # ------------------------------------------------------------------
    # Solvent Prime (MeCN flush)
    # ------------------------------------------------------------------

    def prime_with_solvent(self, flowrate_ul_min, duration_s):
        """
        Flush system with solvent (e.g., MeCN).
        """
        self._require_phase(SegmentationPhase.IDLE)

        # Set the correct valve configuration
        self.runze.carrier_to_dim()
        self.state.runze = RunzeState.CARRIER_TO_DIM

        self.dim.inject()
        self.state.dim = DIMState.INJECT

        self.carrier.set_flow_rate(flowrate_ul_min)
        self.carrier.start_flow()

        time.sleep(duration_s)

        self.carrier.stop_flow()

    # ------------------------------------------------------------------
    # Gas Priming (Create Spacer Geometry)
    # ------------------------------------------------------------------

    def prime_gas_path(self, duration_s):
        """
        Fill inter-valve tubing + sample loop with gas.
        """
        self._require_phase(SegmentationPhase.IDLE)

        # Set valve config for gas routing
        self.runze.gas_to_dim()
        self.state.runze = RunzeState.GAS_TO_DIM
        
        self.dim.inject()
        self.state.dim = DIMState.INJECT

        time.sleep(duration_s)

        self._set_phase(SegmentationPhase.GAS_PRIMED)

    # ------------------------------------------------------------------
    # Reaction Slug Preparation
    # ------------------------------------------------------------------



    # ------------------------------------------------------------------
    # Launch Structured Flow
    # ------------------------------------------------------------------

    def launch_segment(self, flowrate_ul_min):
        self._require_phase(SegmentationPhase.LOOP_LOADED)

        # Orient valves for launch
        self.dim.inject()
        self.state.dim = DIMState.INJECT
        
        self.runze.carrier_to_dim()
        self.state.runze = RunzeState.CARRIER_TO_DIM

        # Start carrier
        self.carrier.set_flow_rate(flowrate_ul_min)
        self.carrier.start_flow()

        # Update state
        self._set_phase(SegmentationPhase.FLOWING)
        print(f"[Segmentation] Segment flowing, carrier running at {flowrate_ul_min} µL/min")

    # ------------------------------------------------------------------
    # Stop Carrier Flow
    # ------------------------------------------------------------------

    def stop_flow(self):
        """
        Stop carrier pump.
        """
        self._require_phase(SegmentationPhase.FLOWING)
        self.carrier.stop_flow()
        self._set_phase(SegmentationPhase.IDLE)

    # ------------------------------------------------------------------
    # Internal Guards + methods
    # ------------------------------------------------------------------

    def _require_phase(self, required_phase):
        if self.state.phase != required_phase:
            raise RuntimeError(
                f"Invalid phase transition: required {required_phase.name}, "
                f"but current phase is {self.state.phase.name}"
            )

    def _set_phase(self, new_phase: SegmentationPhase):
        print(f"[Segmentation] Phase: {self.state.phase.name} -> {new_phase.name}")
        self.state.phase = new_phase

    # ------------------------------------------------------------------
    # Abort + reset methods
    # ------------------------------------------------------------------

    def abort(self):
        """
        Immediately stop all activity and place hardware in a safe state.
        After abort, the system must be explicitly reset before use.
        """

        if self.state.phase == SegmentationPhase.IDLE:
            print("[Segmentation] Abort called, but system is already IDLE.")
            return

        if self.state.phase == SegmentationPhase.ABORTED:
            print("[Segmentation] Abort called, but system is already ABORTED.")
            return

        print(f"[Segmentation] ABORT triggered from phase {self.state.phase.name}")

        
        # --- Stop flow defensively ---
        try:
            self.carrier.stop_flow()
        except Exception as e:
            print(f"[Segmentation] Warning: Failed to stop carrier pump: {e}")
    
        # --- Return valves to safe baseline ---
        try:
            self.runze.carrier_to_dim()
            self.state.runze = RunzeState.CARRIER_TO_DIM
        except Exception as e:
            print(f"[Segmentation] Warning: Failed to reset Runze valve: {e}")
    
        try:
            self.dim.inject()
            self.state.dim = DIMState.INJECT
        except Exception as e:
            print(f"[Segmentation] Warning: Failed to reset DIM valve: {e}")
    
        self._set_phase(SegmentationPhase.ABORTED)
    
        print("[Segmentation] System is now in ABORTED state.")


    def reset(self, flowrate_ul_min, flush_time_sec):
        """
        Reset system after abort
        Flushes fluidic paths and restores a clean IDLE state
        """

        if self.state.phase != SegmentationPhase.ABORTED:
            raise RuntimeError("Reset only allowed from ABORTED state.")
    
        print("[Segmentation] Reset initiated")
        
        # Ensure safe routing
        self.runze.carrier_to_dim()
        self.state.runze = RunzeState.CARRIER_TO_DIM
        
        self.dim.inject()
        self.state.dim = DIMState.INJECT
        
        # Flush
        self.carrier.set_flow_rate(flowrate_ul_min)
        self.carrier.start_flow()
        
        print(f"[Segmentation] Flushing for {flush_time_sec} seconds")
        time.sleep(flush_time_sec)
        
        self.carrier.stop_flow()
        
        self._set_phase(SegmentationPhase.IDLE)
        
        print("[Segmentation] Reset complete. System back to IDLE.")
        