import time
from enum import Enum, auto

class RSGState(Enum):
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()

# TODO - move away from time.sleeps and toward real monitoring for events like pump finished etc

class RSG:
    """
    Reaction Segment Generation (RSG)

    Orchestrates high-level liquid handling actions using:
    - GilsonEthernet (autosampler, owns all motion + safety)
    - AL1000 (syringe pump)

    Design rules:
    - No rack geometry here
    - No vial maps
    - No Z logic
    - No mirroring of Gilson internals
    """

    def __init__(self, gilson, pump):
        self.gilson = gilson
        self.pump = pump
        self.state = RSGState.IDLE

    # ------------------------------------------------------------------
    # Primitive actions
    # ------------------------------------------------------------------
    def _require_idle(self):
        if self.state != RSGState.IDLE:
            raise RuntimeError(f"RSG is busy or in error state: {self.state}")
    
    def pickup_from_vial(self, module_name: str, vial_pos: int, volume: float, rate: float = 0.05):
        print(f"[Pickup] {volume}uL from {module_name} vial {vial_pos} @ {rate}mL/min")
    
        self.gilson.go_into_vial(module_name, vial_pos)
        self.pump.withdraw_volume(volume, rate)
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)

    def dispense_in_vial(self, module_name: str, vial_pos: int, volume: float, rate: float = 0.5):
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
    # Higher-level sequences
    # ------------------------------------------------------------------

    def wash_sequence(self, solvent_volume=100.0, air_gap=5.0):

        print("[Wash] Starting wash sequence")
    
        self._require_idle()
        self.state = RSGState.RUNNING
    
        try:
    
            if air_gap > 0:
                print(f"[Wash] Air gap: {air_gap} µL")
                self.take_air_gap(volume=air_gap, rate=0.05)
    
            print(f"[Wash] Pickup solvent: {solvent_volume} µL")
            self.pickup_from_vial(
                module_name="rack2",
                vial_pos=1,
                volume=solvent_volume,
                rate=0.5
            )
    
            print(f"[Wash] Dispense to waste: {solvent_volume + air_gap} µL")
            self.dispense_in_waste(
                volume=solvent_volume + air_gap,
                rate=0.5
            )
    
            print("[Wash] Complete")
    
            self.state = RSGState.IDLE
    
        except Exception:
            self.state = RSGState.ERROR
            raise

    def build_reaction(self, reaction_plan, air_gap_between: float = 5.0):

        self._require_idle()
        self.state = RSGState.RUNNING
    
        try:
    
            if not isinstance(reaction_plan, list):
                raise TypeError("reaction_plan must be a list of dicts.")
    
            total_volume = 0.0
    
            for i, component in enumerate(reaction_plan):
    
                try:
                    module = component["module"]
                    vial = component["vial"]
                    volume = component["volume"]
                except KeyError:
                    raise ValueError(
                        "Each reaction component must contain "
                        "'module', 'vial', and 'volume'."
                    )
    
                if volume <= 0:
                    raise ValueError("Component volumes must be positive.")
    
                self.pickup_from_vial(
                    module_name=module,
                    vial_pos=vial,
                    volume=volume,
                )
    
                total_volume += volume
    
                if air_gap_between > 0 and i < len(reaction_plan) - 1:
                    self.take_air_gap(air_gap_between)
                    total_volume += air_gap_between
    
            self.state = RSGState.IDLE
    
            return {
                "total_volume_ul": total_volume,
                "num_components": len(reaction_plan),
            }
    
        except Exception:
            self.state = RSGState.ERROR
            raise


    def abort(self):
        self.pump.stop()
        self.gilson.ensure_z_safe()
        self.state = RSGState.ERROR
