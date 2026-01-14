###############################################################################################
# SetupVolumes Class
###############################################################################################


class SetupVolumes:
    """
    Represents the physical volumes (in mL) of different parts of the flow setup.
    These are used to calculate how long it takes to rinse, fill, or reach steady state
    based on given flow rates.

    Essentially: this class turns *flow rates* and *setup geometry* into *timing data*.
    """

    def __init__(
        self,
        volume_valve_to_needle,
        volume_reactor_to_valve,
        volume_before_reactor,
        volume_reactor,
        volume_only_pump_a,
        volume_only_pump_b,
        volume_pump_a_and_pump_b,
        excess=1.5,
    ):
        self.volume_valve_to_needle = volume_valve_to_needle
        self.volume_reactor_to_valve = volume_reactor_to_valve
        self.volume_before_reactor = volume_before_reactor
        self.volume_reactor = volume_reactor
        self.excess = excess
        self.volume_only_pump_a = volume_only_pump_a
        self.volume_only_pump_b = volume_only_pump_b
        self.volume_pump_a_and_pump_b = volume_pump_a_and_pump_b

    # This calculates the time in seconds to fill the volume between valve and needs, given a total flowrate.
    def get_time_fill_needle(self, flowrate_a, flowrate_b, flowrate_sum):
        """Return time in sec to fill the needle at a certain flow rate."""
        duration = ((self.volume_valve_to_needle / flowrate_sum) * self.excess) * 60
        return duration

    # This calculates the the time it takes to reach steady state after switching feeds
    def get_time_stady_state_rinsing(
        self, flowrate_a, flowrate_b, flowrate_sum, stady_state_rinsing_factor
    ):
        """Return time in sec it takes to reach steady state."""
        duration = (
            (
                ((self.volume_reactor * stady_state_rinsing_factor) / flowrate_b)
                + (self.volume_pump_a_and_pump_b / flowrate_sum)
            )
            * self.excess
        ) * 60
        return duration

    # This calculates the time it takes to fill both the volume before the reactor, and the reactor itself
    def get_time_fill_reactor(self, flowrate_a, flowrate_b, flowrate_sum):
        """Return time in sec to fill the reactor."""
        duration = (
            ((self.volume_before_reactor + self.volume_reactor) / flowrate_b)
            * self.excess
        ) * 60
        return duration
