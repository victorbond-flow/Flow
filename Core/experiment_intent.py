from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from copy import deepcopy
import pandas as pd


@dataclass
class ExperimentIntent:
    """
    ExperimentIntent is the *scientific specification layer*.

    It captures:
    - what the experiment is trying to study (intent)
    - how slugs should be generated (design blocks)

    It does NOT:
    - know about hardware
    - know about execution order
    - write files
    - depend on ExperimentBuilder structure directly

    Think of this as:
        "A structured description of an experiment before it becomes a plan."
    """

    experiment_id: str
    description: str = ""

    # Each block defines a *rule for generating slugs*
    blocks: List[Dict[str, Any]] = field(default_factory=list)

    # ------------------------------------------------------------
    # Block definition (v1 simple API)
    # ------------------------------------------------------------

    def add_block(
        self,
        name: str,
        components: List[str],
        ratios: List[List[float]],
        total_volume_uL: float = 100.0,
        fixed_total_volume: bool = True,
    ):
        """
        Adds a design block.

        A block = rule-set that generates one or more slugs.

        Example:
            ratios = [[20,80], [40,60]]

        means:
            slug1 → 20/80 split
            slug2 → 40/60 split

        NOTE:
        - We deliberately store *rules*, not expanded slugs
        - Expansion happens later in .expand()
        """

        block = {
            "name": name,
            "components": components,
            "ratios": ratios,
            "total_volume_uL": total_volume_uL,
            "fixed_total_volume": fixed_total_volume,
        }

        self.blocks.append(block)
        return self  # allows chaining if desired

    # ------------------------------------------------------------
    # Expansion layer (core bridge to existing system)
    # ------------------------------------------------------------

    def expand(self) -> List[Dict[str, Any]]:
        """
        Converts intent → flat slug/component rows.

        This is the ONLY place where we "translate" into the format
        expected by ExperimentBuilder.

        IMPORTANT:
        - This is not chemistry-aware
        - This is not inventory-aware (yet)
        - It is purely structural expansion
        """

        rows = []
        slug_counter = 1

        for block in self.blocks:

            components = block["components"]
            ratios_list = block["ratios"]
            total_volume = block["total_volume_uL"]

            for ratio in ratios_list:

                # Basic sanity check (light-touch, not strict validation layer)
                if len(ratio) != len(components):
                    raise ValueError(
                        f"Ratio {ratio} does not match components {components}"
                    )

                slug_id = f"slug_{slug_counter}"
                slug_counter += 1

                reaction_plan = []

                # Convert ratios → volumes
                # NOTE: intentionally simple; no chemistry logic here
                for comp, r in zip(components, ratio):

                    volume = (r / 100.0) * total_volume

                    reaction_plan.append({
                        "component": comp,   # still symbolic at this stage
                        "volume_uL": volume
                    })

                rows.append({
                    "slug_id": slug_id,
                    "reaction_plan": reaction_plan,
                })

        return rows

    # ------------------------------------------------------------
    # DataFrame conversion (bridge to ExperimentBuilder)
    # ------------------------------------------------------------

    def to_dataframe(self) -> pd.DataFrame:
        """
        Converts expanded intent → row-based format expected by ExperimentBuilder.

        This is intentionally the ONLY coupling point to current system.
        """

        expanded = self.expand()

        flat_rows = []

        for slug in expanded:
            slug_id = slug["slug_id"]

            for comp in slug["reaction_plan"]:
                flat_rows.append({
                    "slug_id": slug_id,
                    "module": None,   # will be resolved later via inventory
                    "vial": None,     # intentionally unresolved at this stage
                    "volume_uL": comp["volume_uL"],
                    "component": comp["component"],
                })

        return pd.DataFrame(flat_rows)

    # ------------------------------------------------------------
    # Human-readable summary (VERY useful for sanity checking)
    # ------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """
        Produces a human-readable view of what the experiment WILL do.

        This is critical for trust in the system.
        """

        summary = {
            "experiment_id": self.experiment_id,
            "description": self.description,
            "num_blocks": len(self.blocks),
            "estimated_slugs": 0,
            "blocks": [],
        }

        for block in self.blocks:
            num_slugs = len(block["ratios"])
            summary["estimated_slugs"] += num_slugs

            summary["blocks"].append({
                "name": block["name"],
                "components": block["components"],
                "num_slugs": num_slugs,
                "total_volume_uL": block["total_volume_uL"],
                "fixed_total_volume": block["fixed_total_volume"],
            })

        return summary