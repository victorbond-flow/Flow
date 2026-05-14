class ProbeState:

    def __init__(self):
        self.reset()


    def reset(self):

        self.air_reserve_ul = 0.0
        self.known = True


    def initialise_air_reserve(
        self,
        volume_ul,
    ):
        self.air_reserve_ul = volume_ul


    def consume_air(
        self,
        volume_ul,
    ):

        if volume_ul > self.air_reserve_ul:
            raise RuntimeError(
                f"Requested {volume_ul} uL "
                f"but only "
                f"{self.air_reserve_ul} uL remains"
            )

        self.air_reserve_ul -= volume_ul


    def remaining_air(self):

        return self.air_reserve_ul


    def invalidate(self):

        self.known = False


    def assert_known(self):

        if not self.known:
            raise RuntimeError(
                "Probe state unknown"
            )