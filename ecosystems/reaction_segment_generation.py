import time
from enum import Enum, auto


class RSGState(Enum):
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()


# TODO - move away from time.sleep and toward real monitoring for pump completion.
class RSG:
    """
    Reaction Segment Generation (RSG)

    Orchestrates high-level liquid handling actions using:
    - GilsonEthernet (autosampler, owns all motion + safety)
    - syringe pump
    - DIM (when slug creation is required)

    Design rules:
    - No rack geometry here
    - No vial maps
    - No Z logic
    - No mirroring of Gilson internals
    """

    def __init__(self, gilson, pump, dim=None):
        self.gilson = gilson
        self.pump = pump
        self.dim = dim
        self.state = RSGState.IDLE

    # ------------------------------------------------------------------
    # Primitive actions
    # ------------------------------------------------------------------
    def _require_idle(self):
        if self.state != RSGState.IDLE:
            raise RuntimeError(f"RSG is busy or in error state: {self.state}")

    def _require_dim(self):
        if self.dim is None:
            raise RuntimeError(
                "RSG requires a DIM instance for this operation. "
                "Instantiate as RSG(gilson, pump, dim)."
            )

    def _normalise_reaction_plan(self, reaction_plan):
        if not isinstance(reaction_plan, list):
            raise TypeError("reaction_plan must be a list of dicts.")

        normalised = []

        for component in reaction_plan:
            if not isinstance(component, dict):
                raise TypeError("Each reaction component must be a dict.")

            try:
                module = component["module"]
                vial = component["vial"]
            except KeyError as exc:
                raise ValueError(
                    "Each reaction component must contain 'module' and 'vial'."
                ) from exc

            volume = component.get(
                "volume",
                component.get("volume_uL", component.get("volume_ul")),
            )
            if volume is None:
                raise ValueError(
                    "Each reaction component must contain 'volume' or 'volume_uL'."
                )

            volume = float(volume)
            if volume <= 0:
                raise ValueError("Component volumes must be positive.")

            normalised.append(
                {
                    "module": module,
                    "vial": vial,
                    "volume_ul": volume,
                    "rate_ml_min": float(component.get("rate", 0.05)),
                }
            )

        return normalised

    def _reaction_plan_from_slug(self, slug_plan):
        if not isinstance(slug_plan, dict):
            raise TypeError("slug_plan must be a dict.")

        if "reaction_plan" in slug_plan:
            return self._normalise_reaction_plan(slug_plan["reaction_plan"])

        if all(key in slug_plan for key in ("module", "vial")):
            volume = slug_plan.get("volume_uL", slug_plan.get("volume"))
            if volume is None:
                raise ValueError(
                    "Single-source slug plans must define 'volume_uL' or 'volume'."
                )

            return self._normalise_reaction_plan(
                [
                    {
                        "module": slug_plan["module"],
                        "vial": slug_plan["vial"],
                        "volume_uL": volume,
                        "rate": slug_plan.get("pickup_rate", 0.05),
                    }
                ]
            )

        raise ValueError(
            "slug_plan must define either 'reaction_plan' or "
            "'module'/'vial' plus 'volume_uL'."
        )

    def initialise(self, air_gap: float = 20.0, rate_wdr: float = 0.25):
        """
        Set up known start condition before any slug sequence.
        Call this once at the beginning of a run, after lines are primed
        with working fluid.
        """
        print("[Initialise] Setting up start condition")

        self._require_idle()
        self.state = RSGState.RUNNING

        try:
            self.take_air_gap(volume=air_gap, rate=rate_wdr)
            self.state = RSGState.IDLE
            print("[Initialise] Ready - air gap in place")
        except Exception:
            self.state = RSGState.ERROR
            raise

    def pickup_from_vial(
    self,
    module_name: str,
    vial_pos: int,
    volume: float,
    rate: float = 0.05,
):
        print(f"[Pickup] {volume}uL from {module_name} vial {vial_pos} @ {rate}mL/min")
    
        self.gilson.go_into_vial(module_name, vial_pos)
        self.pump.withdraw_volume(volume, rate)
    
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)

    def dispense_in_vial(
        self,
        module_name: str,
        vial_pos: int,
        volume: float,
        rate: float = 0.5,
    ):
        print(f"[Dispense] {volume}uL in {module_name} vial {vial_pos} @ {rate}mL/min")

        self.gilson.go_into_vial(module_name, vial_pos)
        self.pump.infuse_volume(volume, rate)
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)

    def dispense_in_waste(self, volume: float, rate: float = 0.5):
        print(f"[Waste] {volume}uL to waste @ {rate}mL/min")

        module_name = "rack2"
        vial_pos = 2

        self.gilson.go_to_vial(module_name, vial_pos)
        self.gilson.go_into_vial(module_name, vial_pos)
        self.pump.infuse_volume(volume, rate)
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)
        self.gilson.ensure_z_safe()

    def dispense_in_dim(self, volume: float, rate: float = 0.5):
        print(f"[DIM] {volume}uL dispensed in DIM @ {rate}mL/min")

        self.gilson.go_into_dim()
        self.pump.infuse_volume(volume, rate)
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)

    def take_air_gap(self, volume: float, rate: float = 0.05):
        print(f"[Air Gap] {volume}uL @ {rate}mL/min")

        self.gilson.ensure_z_safe()
        self.pump.withdraw_volume(volume, rate)
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)

    def prepickup(self, volume: float = 10.0, rate: float = 0.05):
        print(f"[Pre-pickup] {volume}uL from rack2 vial 1 @ {rate} mL/min")

        module_name = "rack2"
        vial_pos = 1

        self.gilson.go_into_vial(module_name, vial_pos)
        self.pump.withdraw_volume(volume, rate)
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)
        self.gilson.ensure_z_safe()

    # ------------------------------------------------------------------
    # Washes
    # ------------------------------------------------------------------
    def needle_wash(self, rate_wdr: float = 0.25, rate_inf: float = 0.5):
        """Wash the needle after a slug charge."""
        print("[Needle Wash] Starting")

        self.gilson.ensure_z_safe()
        self.pump.withdraw_volume(15, rate_wdr)
        time.sleep((15 / (rate_wdr * 1000)) * 60 + 1)

        self.gilson.go_into_vial("rack2", 1)
        self.pump.withdraw_volume(80, rate_wdr)
        time.sleep((80 / (rate_wdr * 1000)) * 60 + 1)

        self.gilson.go_into_vial("rack2", 2)
        self.pump.infuse_volume(95, rate_inf)
        time.sleep((95 / (rate_inf * 1000)) * 60 + 1)

        self.gilson.ensure_z_safe()
        print("[Needle Wash] Complete")

    def dim_wash(self, rate_wdr: float = 0.25, rate_inf: float = 0.5):
        """Flush the DIM dead volume after a slug charge."""
        print("[DIM Wash] Starting")

        self.gilson.ensure_z_safe()
        self.pump.withdraw_volume(15, rate_wdr)
        time.sleep((15 / (rate_wdr * 1000)) * 60 + 1)

        self.gilson.go_into_vial("rack2", 1)
        self.pump.withdraw_volume(50, rate_wdr)
        time.sleep((50 / (rate_wdr * 1000)) * 60 + 1)

        self.gilson.go_into_dim()
        self.pump.infuse_volume(65, rate_inf)
        time.sleep((65 / (rate_inf * 1000)) * 60 + 1)

        self.gilson.ensure_z_safe()
        print("[DIM Wash] Complete")

    def between_slug_wash(self, rate_wdr: float = 0.25, rate_inf: float = 0.5):
        """Full between-slug wash. Needle wash followed by DIM wash."""
        print("[Between Slug Wash] Starting")

        self._require_idle()
        self.state = RSGState.RUNNING

        try:
            self.needle_wash(rate_wdr=rate_wdr, rate_inf=rate_inf)
            self.dim_wash(rate_wdr=rate_wdr, rate_inf=rate_inf)
            self.state = RSGState.IDLE
            print("[Between Slug Wash] Complete")
        except Exception:
            self.state = RSGState.ERROR
            raise

    # ------------------------------------------------------------------
    # Higher-level sequences
    # ------------------------------------------------------------------
    def assemble_reaction(
    self,
    reaction_plan,
    air_gap_between: float = 5.0,
    post_pickup_air_gap: float = 5.0,
    withdraw_rate: float = None,
):
        self._require_idle()
        self.state = RSGState.RUNNING
    
        try:
            reaction_plan = self._normalise_reaction_plan(reaction_plan)
    
            total_volume = 0.0
            n = len(reaction_plan)
    
            for i, component in enumerate(reaction_plan):
    
                # 1. pickup component
                self.pickup_from_vial(
                    module_name=component["module"],
                    vial_pos=component["vial"],
                    volume=component["volume_ul"],
                    rate=(
                        withdraw_rate
                        if withdraw_rate is not None
                        else component["rate_ml_min"]
                )
                )
    
                total_volume += component["volume_ul"]
    
                # 2. between-component air gap (only if NOT last component)
                if i < n - 1 and air_gap_between > 0:
                    self.take_air_gap(air_gap_between)
                    total_volume += air_gap_between
    
            # 3. post-pickup air gap (ONLY once per slug, after final component)
            if post_pickup_air_gap > 0:
                self.take_air_gap(post_pickup_air_gap)
                total_volume += post_pickup_air_gap
    
            self.state = RSGState.IDLE
    
            return {
                "total_volume_ul": total_volume,
                "num_components": n,
            }
    
        except Exception:
            self.state = RSGState.ERROR
            raise

    def build_reaction(self, reaction_plan, air_gap_between: float = 5.0):
        """
        Backward-compatible wrapper for existing notebooks.
        Prefer assemble_reaction() for new code.
        """
        return self.assemble_reaction(
            reaction_plan=reaction_plan,
            air_gap_between=air_gap_between,
        )

    def build_rxn_segment(
        self,
        slug_plan,
        air_gap_between: float = 5.0,
        dispense_rate: float = 0.5,
        withdraw_rate: float = None,
    ):
        """
        Build a liquid reaction segment and charge it into the DIM loop.

        Assumes:
        - Segmentation layer has already positioned DIM in LOAD
        - Gas spacer geometry has already been established externally

        Responsibilities:
        1. normalise slug plan
        2. aspirate components into syringe line
        3. optionally place internal air gaps between components
        4. dispense full liquid segment into DIM loop

        Does NOT:
        - generate gas spacers
        - switch DIM to INJECT
        - launch carrier flow
        """

        self._require_dim()

        reaction_plan = self._reaction_plan_from_slug(slug_plan)
        slug_id = slug_plan.get("slug_id", "untracked-segment")

        print(f"[Build Reaction Segment] {slug_id}")

        # DIM should already be in LOAD from Segmentation
        self.dim.assert_load()

        result = self.assemble_reaction(
            reaction_plan=reaction_plan,
            air_gap_between=air_gap_between,
            withdraw_rate=withdraw_rate
        )

        self.dispense_in_dim(
            volume=result["total_volume_ul"],
            rate=dispense_rate,
        )

        return {
            "slug_id": slug_id,
            "dispensed_volume_ul": result["total_volume_ul"],
            "num_components": result["num_components"],
            "air_gap_between_ul": air_gap_between,
        }

    def abort(self):
        self.pump.stop()
        self.gilson.ensure_z_safe()
        self.state = RSGState.ERROR
