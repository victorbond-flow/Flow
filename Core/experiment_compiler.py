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
    slug_order: Optional[int] = None
    component_order: Optional[int] = None


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

    OUTPUT_COLUMNS = [
        "slug_id",
        "module",
        "vial",
        "volume_uL",
        "component",
        "block_id",
        "slug_order",
        "component_order",
    ]

    def compile(self, intent: Dict[str, Any]) -> pd.DataFrame:
        intent = self._coerce_intent(intent)
    
        rows = []
        experiment_id = intent.get("experiment_id", "EXPT")
        blocks = intent["blocks"]
    
        for block_index, block in enumerate(blocks):
            block_rows = self._expand_block(
                block=block,
                block_index=block_index,
                experiment_id=experiment_id,
            )
            rows.extend(block_rows)
    
        if not rows:
            raise ValueError("Compilation produced no rows")
    
        # enforce strict schema BEFORE dataframe conversion
        data = [r.__dict__ for r in rows]
    
        for i, r in enumerate(data):
            missing = [c for c in self.OUTPUT_COLUMNS if c not in r]
            if missing:
                raise ValueError(f"Row {i} missing columns: {missing}")
    
        return pd.DataFrame(data)[self.OUTPUT_COLUMNS]

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
        if not slug_spec:
            raise ValueError("slug_spec must contain at least one slug")

        slugs = []
        for slug_id, composition in slug_spec:
            if not composition:
                raise ValueError(f"{slug_id} has no components")

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

    def _coerce_intent(self, intent):
        if isinstance(intent, dict):
            coerced = intent
        elif hasattr(intent, "experiment_id") and hasattr(intent, "blocks"):
            coerced = {
                "experiment_id": intent.experiment_id,
                "blocks": intent.blocks,
            }
        else:
            raise TypeError("intent must be a dict or ExperimentIntent-like object")
    
        if "blocks" not in coerced or coerced["blocks"] is None:
            raise ValueError("Intent must contain blocks")
    
        if len(coerced["blocks"]) == 0:
            raise ValueError("Intent must contain at least one block")
    
        return coerced

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
        block_id = block.get("block_id", f"block_{block_index + 1}")
    
        slug_definitions = block.get("slugs")
    
        if slug_definitions is None:
            raise ValueError(f"{block_id} must contain slugs")
    
        if len(slug_definitions) == 0:
            raise ValueError(f"{block_id} has no slugs")
    
        expanded_rows = []
    
        for i, slug in enumerate(slug_definitions):
            slug_id = slug.get("slug_id", f"{block_id}_slug_{i + 1}")
    
            composition = slug.get("composition")
    
            if not composition:
                raise ValueError(f"{slug_id} has no composition")
    
            for j, item in enumerate(composition, start=1):
                component_name, volume_uL = self._normalise_component(item)
    
                resolved = self._resolve_component(component_name)
    
                expanded_rows.append(
                    CompiledRow(
                        slug_id=slug_id,
                        module=resolved["module"],
                        vial=resolved["vial"],
                        volume_uL=float(volume_uL),
                        component=component_name,
                        block_id=block_id,
                        slug_order=i + 1,            # compiler is authority
                        component_order=j,           # compiler is authority
                    )
                )
    
        return expanded_rows

    def _expand_ratio_block(self, block, block_id):
        components = block.get("components", [])
        ratios = block.get("ratios", [])
        total_volume = float(block.get("total_volume_uL", 0))

        if not components:
            raise ValueError(f"{block_id} must define components")

        if total_volume <= 0:
            raise ValueError(f"{block_id}: total_volume_uL must be > 0")

        slugs = []
        for i, ratio in enumerate(ratios, start=1):
            if len(ratio) != len(components):
                raise ValueError(
                    f"{block_id} ratio {ratio} does not match components {components}"
                )

            ratio_total = sum(float(value) for value in ratio)
            if ratio_total <= 0:
                raise ValueError(f"{block_id} ratio total must be > 0")

            composition = []
            for component, ratio_value in zip(components, ratio):
                volume = (float(ratio_value) / ratio_total) * total_volume
                composition.append(
                    {
                        "component": component,
                        "volume_uL": volume,
                    }
                )

            slugs.append(
                {
                    "slug_id": f"{block_id}_slug_{i}",
                    "composition": composition,
                }
            )

        return slugs

    def _normalise_component(self, item):
        if isinstance(item, dict):
            name = item.get("component") or item.get("name")
            volume = item.get("volume_uL") or item.get("volume")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            name, volume = item
        else:
            raise ValueError(f"Invalid component format: {item}")
    
        if not name:
            raise ValueError("Component missing name")
    
        try:
            volume = float(volume)
        except Exception:
            raise ValueError(f"{name}: volume must be numeric")
    
        if volume <= 0:
            raise ValueError(f"{name}: volume_uL must be > 0")
    
        return name, volume

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
