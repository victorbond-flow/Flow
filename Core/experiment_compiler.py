from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd


@dataclass
class CompiledRow:
    slug_id: str
    module: str
    vial: int
    volume_uL: float
    component: str
    block_id: Optional[str] = None


class ExperimentCompiler:
    """
    Translates ExperimentIntent → physical slug dataframe.

    Responsibilities:
    - Resolve chemical names via Inventory
    - Expand blocks into slug-level rows
    - Output Builder-compatible dataframe

    This is NOT concerned with:
    - hardware execution
    - JSON formatting
    - scheduling
    """

    def __init__(self, inventory):
        self.inventory = inventory

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def compile(self, intent: Dict[str, Any]) -> pd.DataFrame:
        """
        Main entry point.

        Parameters
        ----------
        intent : dict
            Must contain:
                - experiment_id
                - blocks: list of block definitions

        Returns
        -------
        pd.DataFrame (Builder-compatible)
        """

        rows = []

        blocks = intent.get("blocks", [])
        experiment_id = intent.get("experiment_id", "EXPT")

        for block_index, block in enumerate(blocks):
            block_rows = self._expand_block(
                block=block,
                block_index=block_index,
                experiment_id=experiment_id
            )
            rows.extend(block_rows)

        return pd.DataFrame([r.__dict__ for r in rows])

    def normalise(self, experiment_id, slug_spec, block_id="block_1"):
        """
        Convert a compact slug specification into canonical experiment intent.
    
        Purpose
        -------
        This is a structural transformation layer only.
        It does NOT interpret chemistry, ratios, or experimental meaning.
    
        Input format (human-friendly):
            [
                ("slug_1", [("MeCN", 20), ("MeCN", 80)]),
                ...
            ]
    
        Output format (compiler-ready intent):
            {
                "experiment_id": ...,
                "blocks": [
                    {
                        "block_id": ...,
                        "slugs": [
                            {
                                "slug_id": ...,
                                "composition": [...]
                            }
                        ]
                    }
                ]
            }
        """
    
        # Basic structural conversion
        slugs = []
        for slug_id, composition in slug_spec:
            slugs.append({
                "slug_id": slug_id,
                "composition": composition
            })
    
        intent = {
            "experiment_id": experiment_id,
            "blocks": [
                {
                    "block_id": block_id,
                    "slugs": slugs
                }
            ]
        }
    
        return intent

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def summarise_slugs(self, df):
        grouped = df.groupby("slug_id")
    
        summary = pd.DataFrame({
            "slug_id": grouped.size().index,
            "n_components": grouped.size().values,
            "total_volume_uL": grouped["volume_uL"].sum().values,
            "components": [
                list(zip(group["component"].values, group["volume_uL"].values))
                for _, group in grouped
            ]
        })
    
        return summary

    # ------------------------------------------------------------
    # Block expansion
    # ------------------------------------------------------------

    def _expand_block(self, block, block_index, experiment_id):
        """
        Expands a single block into multiple slugs.
        """

        block_id = block.get("block_id", f"block_{block_index}")

        slug_definitions = block["slugs"]

        expanded_rows = []

        for i, slug in enumerate(slug_definitions):
            slug_id = slug.get("slug_id", f"{block_id}_slug_{i}")

            composition = slug["composition"]  # list of (name, volume_uL)

            for component_name, volume_uL in composition:

                resolved = self._resolve_component(component_name)

                expanded_rows.append(
                    CompiledRow(
                        slug_id=slug_id,
                        module=resolved["module"],
                        vial=resolved["vial"],
                        volume_uL=float(volume_uL),
                        component=component_name,
                        block_id=block_id,
                    )
                )

        return expanded_rows

    # ------------------------------------------------------------
    # Inventory resolution
    # ------------------------------------------------------------

    def _resolve_component(self, name: str) -> Dict[str, Any]:
        """
        Maps chemical name → physical vial.
        """

        record = self.inventory.lookup(name)

        return {
            "module": record["module"],
            "vial": record["vial"],
        }