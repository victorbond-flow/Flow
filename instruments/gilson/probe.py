class ProbeState:

    def __init__(self):
        self.reset()

    def reset(self):
        self.contents = [
            {
                "type": "working_fluid",
                "volume_ul": float("inf"),  # reservoir, but still uniform structure
                "is_infinite": True,
            }
        ]
        self.known = True

    # ------------------------------------------------------------
    # ADD SEGMENT
    # ------------------------------------------------------------
    def add(self, fluid_type, volume_ul):
        self.contents.append(
            {
                "type": fluid_type,
                "volume_ul": float(volume_ul),
                "is_infinite": False,
            }
        )

    # ------------------------------------------------------------
    # CONSUME (stack-based displacement model)
    # ------------------------------------------------------------
    def consume(self, volume_ul):
        remaining = volume_ul

        while remaining > 0 and self.contents:

            segment = self.contents[-1]

            # infinite reservoir cannot be depleted
            if segment.get("is_infinite", False):
                raise RuntimeError(
                    "Attempted to consume from infinite reservoir segment"
                )

            if segment["volume_ul"] <= remaining:
                remaining -= segment["volume_ul"]
                self.contents.pop()

            else:
                segment["volume_ul"] -= remaining
                remaining = 0

    # ------------------------------------------------------------
    # STATUS (human readable only)
    # ------------------------------------------------------------
    def status(self):
        parts = []

        for x in self.contents:
            if x.get("is_infinite", False):
                parts.append(f"[{x['type']}]")
            else:
                parts.append(f"[{x['type']} ({x['volume_ul']} uL)]")

        return " ".join(parts)

    # ------------------------------------------------------------
    # INVALIDATION
    # ------------------------------------------------------------
    def invalidate(self):
        self.known = False

    def assert_known(self):
        if not self.known:
            raise RuntimeError("Probe state unknown")