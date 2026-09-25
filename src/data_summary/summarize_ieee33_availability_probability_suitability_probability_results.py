import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"


# =========================================================
# TWO-FACTOR DATA SUMMARY
# =========================================================

def create_availability_probability_suitability_probability_summary():
    """
    Calculate mean IEEE 33-bus results by availability and suitability 
    probabilities.
    """

    input_path = (
        DATA_DIR
        / (
            "ieee33_availability_probability_"
            "suitability_probability_results.csv"
        )
    )

    output_path = (
        DATA_DIR
        / (
            "ieee33_availability_probability_"
            "suitability_probability_summary.csv"
        )
    )

    df = pd.read_csv(input_path)

    summary_columns = [
        "quantity_assignments",
        "quality_assignments",
        "aggregate_value_assignments",

        "quantity_assignment_value",
        "quality_assignment_value",
        "aggregate_value_assignment_value",

        "quantity_highest_priority",
        "quality_highest_priority",
        "aggregate_value_highest_priority",

        "quantity_secondary_priority",
        "quality_secondary_priority",
        "aggregate_value_secondary_priority",

        "quantity_time",
        "quality_time",
        "aggregate_value_time",
    ]

    summary = (
        df.groupby(
            [
                "availability_probability",
                "suitability_probability",
            ]
        )[summary_columns]
        .mean()
        .reset_index()
    )

    summary.to_csv(
        output_path,
        index=False,
    )

    print(
        "\n=== IEEE 33-BUS AVERAGES BY AVAILABILITY PROBABILITY "
        "AND SUITABILITY PROBABILITY ==="
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print("\nFile saved:")
    print(f" - {output_path}")

    return summary


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    create_availability_probability_suitability_probability_summary()