"""
Generate a local factorial design for syringe pump validation.

Outputs a CSV with all unique combinations of factors.
"""
import os
from datetime import date
from pyDOE2 import fullfact
import pandas as pd
from pathlib import Path

def create_factorial_design(center, factor_levels, factor_names, labbook_entry, output_dir=None):
    """
    Generates a full factorial design and saves it to CSV.

    Parameters:
    - center: dict of center point (just for reference)
    - factor_levels: dict of factor: [low, high]
    - factor_names: list of factor names in order
    - labbook_entry: str, lab book entry ID for filename
    - output_dir: folder to save CSV (defaults to Design/outputs)
    
    Returns:
    - df: pandas DataFrame of unique factorial runs
    """

    # --------------------------------------------------
    # Resolve output folder
    # --------------------------------------------------
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

    if output_dir is None:
        output_dir = PROJECT_ROOT / "Design" / "outputs"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # Generate full factorial combinations
    # --------------------------------------------------
    levels_per_factor = [len(v) for v in factor_levels.values()]
    design_matrix = fullfact(levels_per_factor)

    runs = []
    for row in design_matrix:
        runs.append([factor_levels[factor_names[i]][int(row[i])] for i in range(len(factor_names))])

    df = pd.DataFrame(runs, columns=factor_names)

    # --------------------------------------------------
    # Add design_id column
    # --------------------------------------------------
    df.insert(
        0,
        "design_id",
        [f"{labbook_entry}_D{str(i+1).zfill(2)}" for i in range(len(df))]
    )

    # --------------------------------------------------
    # Save CSV
    # --------------------------------------------------
    today = date.today().isoformat()
    filename = f"factorial_runs_{labbook_entry}_{today}.csv"
    csv_path = output_dir / filename
    df.to_csv(csv_path, index=False)

    print(f"Factorial design saved to:\n{csv_path.resolve()}")

    return df


