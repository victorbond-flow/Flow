class FakeDIM:
    def load(self):
        print("[FAKE DIM] Switched to LOAD")

    def inject(self):
        print("[FAKE DIM] Switched to INJECT")


class FakeRunze:
    def go_to_pos(self, pos):
        print(f"[FAKE RUNZE] Moved to position {pos}")


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
