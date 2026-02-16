import time
from enum import Enum, auto


class SegmentationState(Enum):
    """
    Enumerates the allowed high-level states of the segmentation system.

    These states define the valid progression of a segmented flow run
    and are used to guard against invalid hardware operations.
    """
    IDLE = auto()
    GAS_PRIMED = auto()
    LOOP_LOADED = auto()
    FLOWING = auto()


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

        self.state = SegmentationState.IDLE

    # ------------------------------------------------------------------
    # Solvent Prime (MeCN flush)
    # ------------------------------------------------------------------

    def prime_with_solvent(self, flowrate_ul_min, duration_s):
        """
        Flush system with solvent (e.g., MeCN).
        """
        self._require_state(SegmentationState.IDLE)

        # Carrier → DIM → reactor
        self.runze.go_to_pos(2)
        self.dim.inject()

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
        self._require_state(SegmentationState.IDLE)

        # Gas → DIM → waste
        self.runze.go_to_pos(1)
        self.dim.inject()

        time.sleep(duration_s)

        self.state = SegmentationState.GAS_PRIMED

    # ------------------------------------------------------------------
    # Reaction Slug Preparation
    # ------------------------------------------------------------------

    def load_reaction_slug(self, recipe):
        """
        Load reaction mixture into sample loop via RSG.
        Gas spacers must already exist.
        """
        self._require_state(SegmentationState.GAS_PRIMED)

        # Isolate inter-valve gas volumes
        self.dim.load()

        # Delegate mixture formation to RSG
        self.rsg.prepare_reaction(recipe)

        self.state = SegmentationState.LOOP_LOADED

    # ------------------------------------------------------------------
    # Launch Structured Flow
    # ------------------------------------------------------------------

    def launch_segment(self, flowrate_ul_min):
        """
        Begin structured segmented flow.
        """
        self._require_state(SegmentationState.LOOP_LOADED)

        # Orient valves for launch
        self.dim.inject()
        self.runze.go_to_pos(2)  # carrier → DIM → reactor

        # Start carrier
        self.carrier.set_flow_rate(flowrate_ul_min)
        self.carrier.start_flow()

        self.state = SegmentationState.FLOWING

    # ------------------------------------------------------------------
    # Stop Carrier Flow
    # ------------------------------------------------------------------

    def stop_flow(self):
        """
        Stop carrier pump.
        """
        self._require_state(SegmentationState.FLOWING)

        self.carrier.stop_flow()

        self.state = SegmentationState.IDLE

    # ------------------------------------------------------------------
    # Internal Guard
    # ------------------------------------------------------------------

    def _require_state(self, required_state):
        if self.state != required_state:
            raise RuntimeError(
                f"Invalid state transition: required {required_state}, "
                f"but current state is {self.state}"
            )
