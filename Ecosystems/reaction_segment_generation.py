# Standard imports
import time

# Local imports
from Instruments.GX_271.gilson_ethernet import GilsonEthernet
from Instruments.WPI_Syr_pump.Pump import AL1000


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

    def __init__(self, gilson, pump, syringe_diameter=4.606):
        self.gilson = gilson
        self.pump = pump
        self.syringe_diameter = syringe_diameter

    # ------------------------------------------------------------------
    # Primitive actions
    # ------------------------------------------------------------------

    def pickup_from_vial(
        self,
        module_name: str,
        vial_pos: int,
        volume: float,
        rate: float = 0.05,
    ):
        """
        Withdraw liquid from a vial.
        """

        # Move into vial (Gilson handles all Z safety)
        self.gilson.go_into_vial(module_name, vial_pos)

        # Configure pump (units are fixed by AL1000 firmware)
        self.pump.prepare(
            rate=rate,
            volume=volume,
            direction="WDR",
        )

        # Start withdrawal
        self.pump.start()

        # Temporary timing-based wait
        wait_time = (volume / (rate * 1000)) * 60  # seconds
        time.sleep(wait_time + 1)

        self.pump.stop()

        # No explicit Z move here — next XY move will be safe by design

    def dispense_in_vial(
        self,
        module_name: str,
        vial_pos: int,
        volume: float,
        rate: float = 0.5,
    ):
        """
        Infuse liquid into a vial.
        """

        # Move into vial
        self.gilson.go_into_vial(module_name, vial_pos)

        # Configure pump
        self.pump.prepare(
            rate=rate,
            volume=volume,
            direction="INF",
        )

        # Start infusion
        self.pump.start()

        # Temporary timing-based wait
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)

        self.pump.stop()

    def dispense_in_waste(
        self,
        volume: float,
        rate: float = 0.5,
    ):
        """
        Dispense liquid into the waste Duran.
        Waste location is fixed:
            module_name = "rack2"
            vial_pos    = 2
        """

        module_name = "rack2"
        vial_pos = 2

        # Move above waste vial safely
        self.gilson.go_to_vial(module_name, vial_pos)

        # Move into waste vial
        self.gilson.go_into_vial(module_name, vial_pos)

        # Configure pump for dispense
        self.pump.prepare(
            rate=rate,
            volume=volume,
            direction="INF",
        )

        # Start dispense
        self.pump.start()

        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)

        self.pump.stop()

        # Retract to safe Z
        self.gilson.ensure_z_safe()


    def dispense_in_dim(
        self,
        volume: float,
        rate: float = 0.5,
    ):
        """
        Dispense liquid into the DIM.
        Valve state and Z safety are handled by Gilson.
        """
    
        # Move into DIM (asserts correct valve state internally)
        self.gilson.go_into_dim()
    
        # Configure pump
        self.pump.prepare(
            rate=rate,
            volume=volume,
            direction="INF",
        )
    
        self.pump.start()
    
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)
    
        self.pump.stop()
    
        # Retract safely
        self.gilson.leave_dim()




    def take_air_gap(
        self,
        volume: float,
        rate: float = 0.05,
    ):
        """
        Withdraw an air gap after ensuring the probe isnt in any liquid
        """

        # Ensure the probe is above all modules / liquid
        self.gilson.ensure_z_safe()
        
        # Configure the pump
        self.pump.prepare(
            rate=rate,
            volume=volume,
            direction="WDR",
        )

        # Start withdrawal, and wait for a length of time calculated based on the volume and rate
        self.pump.start()

        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1) # +1 second just to be ssafe

        self.pump.stop()

    def prepickup(self, volume: float = 10.0, rate: float = 0.05):
        """
        Pre-pickup step:
        - Always goes to rack2, vial 1
        - Withdraws `volume` µL (default 10 µL)
        """
        module_name = "rack2"
        vial_pos = 1
    
        # Move safely + into vial (Gilson handles Z safety internally)
        self.gilson.go_into_vial(module_name, vial_pos)
    
        # Prepare pump
        self.pump.prepare(
            rate=rate,
            volume=volume,
            direction="WDR"
        )
    
        # Start pump
        self.pump.start()
    
        # Temporary blocking wait
        wait_time = (volume / (rate * 1000)) * 60
        time.sleep(wait_time + 1)
    
        self.pump.stop()
    
        # Leave vial safely
        self.gilson.ensure_z_safe()



    # ------------------------------------------------------------------
    # Higher-level sequences
    # ------------------------------------------------------------------

    def wash_sequence(
    self,
    solvent_volume: float = 100.0,
    air_gap: float = 5.0,
):
        """
        Withdraw a small air gap, then solvent from rack2 vial 1,
        and dispense everything into the waste vial (rack2, vial 2).
    
        Parameters:
        - solvent_volume: µL of liquid to withdraw from rack2 vial 1
        - air_gap: µL of air to add before the liquid
        """
    
        # 1) Take air gap at slow rate
        if air_gap > 0:
            self.take_air_gap(volume=air_gap, rate=0.05)
    
        # 2) Withdraw solvent at faster rate
        self.pickup_from_vial(module_name="rack2", vial_pos=1, volume=solvent_volume, rate=0.5)
    
        # 3) Dispense everything into waste at same fast rate
        self.dispense_in_waste(volume=solvent_volume + air_gap, rate=0.5)




