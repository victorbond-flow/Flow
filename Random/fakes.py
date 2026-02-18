class FakeDIM:
    def __init__(self):
        self.position = None  # track the current position
    
    def load(self):
        self.position = "B"
        print("[FAKE DIM] Switched to LOAD")
    
    def inject(self):
        self.position = "A"
        print("[FAKE DIM] Switched to INJECT")
    
    def read_pos(self):
        return self.position or "?"

    def assert_load(self):
        if self.read_pos() != "B":
            raise RuntimeError(f"DIM must be in LOAD. Current position: {self.read_pos()}")
        print("[FAKE DIM] assert_load passed")
    
    def assert_inject(self):
        if self.read_pos() != "A":
            raise RuntimeError(f"DIM must be in INJECT. Current position: {self.read_pos()}")
        print("[FAKE DIM] assert_inject passed")

class FakeRunze:
    def __init__(self):
        self.position = None  # track the current position

    def go_to_pos(self, pos):
        if self.position == pos:
            print(f"[FAKE RUNZE] Already at position {pos}")
        else:
            self.position = pos
            print(f"[FAKE RUNZE] Moved to position {pos}")

    def read_pos(self):
        return self.position or "?"

    def assert_pos(self, expected_pos):
        if self.position != expected_pos:
            raise RuntimeError(
                f"Runze must be in position {expected_pos}, "
                f"but current position is {self.position}"
            )
        print(f"[FAKE RUNZE] assert_pos passed ({expected_pos})")

class FakePump:
    def set_flow_rate(self, rate):
        print(f"[FAKE PUMP] Flow rate set to {rate}")

    def start_flow(self):
        print("[FAKE PUMP] Flow started")

    def stop_flow(self):
        print("[FAKE PUMP] Flow stopped")

class FakeGilson:
    def go_into_vial(self, module_name, vial_pos):
        print(f"[Gilson] go_into_vial -> {module_name}, {vial_pos}")

    def go_to_vial(self, module_name, vial_pos):
        print(f"[Gilson] go_to_vial -> {module_name}, {vial_pos}")

    def ensure_z_safe(self):
        print("[Gilson] ensure_z_safe")

    def go_into_dim(self):
        print("[Gilson] go_into_dim")

    def leave_dim(self):
        print("[Gilson] leave_dim")

class FakeSyrPump:
    def prepare(self, rate, volume, direction):
        print(f"[Pump] prepare -> rate={rate}, volume={volume}, dir={direction}")

    def start(self):
        print("[Pump] start")

    def stop(self):
        print("[Pump] stop")
