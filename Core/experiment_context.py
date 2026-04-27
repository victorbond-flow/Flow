from dataclasses import dataclass
from typing import Optional

@dataclass
class ExperimentContext:
    experiment_id: str
    plan: dict
    slug_index: int = 0
    active: bool = True


class ExperimentManager:
    def __init__(self):
        self.mode = "untracked"   # default state
        self.context: Optional[ExperimentContext] = None

    def start_experiment(self, experiment_id: str, plan: dict):
        if self.mode == "experiment":
            raise Exception(f"Experiment already running: {self.context.experiment_id}")

        self.context = ExperimentContext(
            experiment_id=experiment_id,
            plan=plan,
            slug_index=0,
            active=True
        )

        self.mode = "experiment"
        print(f"[EXPERIMENT MODE] Started {experiment_id}")

    def end_experiment(self):
        if self.mode == "untracked":
            print("[EXPERIMENT MODE] No active experiment")
            return

        print(f"[EXPERIMENT MODE] Ending {self.context.experiment_id}")

        self.context = None
        self.mode = "untracked"

    def is_experiment_active(self) -> bool:
        return self.mode == "experiment"

    def get_next_slug(self):
        if not self.is_experiment_active():
            return None

        slugs = self.context.plan["slugs"]
        slug = slugs[self.context.slug_index]
        self.context.slug_index += 1
        return slug