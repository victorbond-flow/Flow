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
