from dataclasses import dataclass, field
from typing import List, Dict, Any
import pandas as pd


@dataclass
class ExperimentIntent:
    """
    ExperimentIntent = scientific experiment specification layer.

    PURPOSE:
    - Describe *what experiment is being done*
    - NOT how it is executed
    - NOT how slugs are physically constructed

    OUTPUT:
    - A structured intermediate representation that ExperimentCompiler consumes
    """

    experiment_id: str
    description: str = ""

    # Low-level fallback structure (still used by compiler)
    blocks: List[Dict[str, Any]] = field(default_factory=list)

    # ============================================================
    # HIGH-LEVEL API (NEW)
    # ============================================================

    def repeat(
        self,
        component: str,
        volume_uL: float,
        n: int,
        name: str = "repeat_block",
    ):
        """
        Simple repetition experiment:
            same composition repeated N times
        """

        block = {
            "name": name,
            "components": [component],
            "ratios": [[100] for _ in range(n)],
            "total_volume_uL": volume_uL,
            "fixed_total_volume": True,
        }

        self.blocks.append(block)
        return self

    def series(
        self,
        component: str,
        solvent: str,
        concentrations: List[float],
        volume_uL: float,
        name: str = "series_block",
    ):
        """
        Simple 2-component series (e.g. dilution series).

        NOTE:
        This keeps logic simple and defers chemistry interpretation
        to user-level correctness.
        """

        ratios = []

        for c in concentrations:
            ratios.append([c * 100, (1 - c) * 100])

        block = {
            "name": name,
            "components": [component, solvent],
            "ratios": ratios,
            "total_volume_uL": volume_uL,
            "fixed_total_volume": True,
        }

        self.blocks.append(block)
        return self

    # ============================================================
    # LEGACY API (still supported)
    # ============================================================

    def add_block(
        self,
        name: str,
        components: List[str],
        ratios: List[List[float]],
        total_volume_uL: float = 100.0,
        fixed_total_volume: bool = True,
    ):
        """
        Low-level block definition (kept for backward compatibility).
        Prefer repeat()/series() where possible.
        """

        block = {
            "name": name,
            "components": components,
            "ratios": ratios,
            "total_volume_uL": total_volume_uL,
            "fixed_total_volume": fixed_total_volume,
        }

        self.blocks.append(block)
        return self

    # ============================================================
    # EXPANSION (unchanged contract for compiler)
    # ============================================================

    def expand(self) -> List[Dict[str, Any]]:
        """
        Converts intent → compiler-readable structure.

        IMPORTANT:
        - This is NOT chemical logic
        - This is NOT hardware logic
        - It is purely structural expansion
        """

        rows = []
        slug_counter = 1

        for block in self.blocks:

            components = block["components"]
            ratios_list = block["ratios"]
            total_volume = block["total_volume_uL"]

            for ratio in ratios_list:

                if len(ratio) != len(components):
                    raise ValueError(
                        f"Ratio {ratio} does not match components {components}"
                    )

                slug_id = f"slug_{slug_counter}"
                slug_counter += 1

                reaction_plan = []

                for comp, r in zip(components, ratio):

                    volume = (r / 100.0) * total_volume
                
                    if isinstance(comp, str):
                        comp = {
                            "name": comp,
                            "concentration_M": None,
                            "solvent": None,
                        }
                
                    reaction_plan.append({
                        "component": comp["name"],
                        "concentration_M": comp["concentration_M"],
                        "solvent": comp["solvent"],
                        "volume_uL": volume,
                    })

                rows.append({
                    "slug_id": slug_id,
                    "reaction_plan": reaction_plan,
                })

        return rows

    # ============================================================
    # COMPILER BRIDGE
    # ============================================================

    def to_dataframe(self) -> pd.DataFrame:
        expanded = self.expand()

        flat_rows = []

        for slug in expanded:
            slug_id = slug["slug_id"]

            for comp in slug["reaction_plan"]:
                flat_rows.append({
                    "slug_id": slug_id,
                    "module": None,
                    "vial": None,
                    "volume_uL": comp["volume_uL"],
                    "component": comp["component"],
                })

        return pd.DataFrame(flat_rows)

    # ============================================================
    # INSPECTION
    # ============================================================

    def summary(self) -> Dict[str, Any]:

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