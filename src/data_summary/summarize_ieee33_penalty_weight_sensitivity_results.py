import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"


# =========================================================
# PENALTY-WEIGHT SENSITIVITY DATA SUMMARY
# =========================================================

def create_penalty_weight_sensitivity_summary():
    """
    Create a summary of the IEEE 33-bus
    penalty-weight sensitivity results.
    """

    input_path = (
        DATA_DIR
        / "ieee33_penalty_weight_sensitivity_results.csv"
    )

    output_path = (
        DATA_DIR
        / "ieee33_penalty_weight_sensitivity_summary.csv"
    )

    df = pd.read_csv(input_path)

    summary_columns = [
        "qty_assignment_value",
        "qty_highest_priority",
        "qty_secondary_priority",
        "qty_average_slack",

        "qual_assignment_value",
        "qual_highest_priority",
        "qual_secondary_priority",
        "qual_average_slack",

        "w_assignment_value",
        "w_highest_priority",
        "w_secondary_priority",
    ]

    summary = (
        df.groupby(
            "penalty_weight"
        )[summary_columns]
        .mean()
        .reindex(
            [
                0.25,
                0.50,
                1.00,
                2.00,
            ]
        )
        .reset_index()
    )

    summary.to_csv(
        output_path,
        index=False,
    )

    print(
        "\n=== IEEE 33-BUS AVERAGES "
        "BY PENALTY WEIGHT ==="
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
    create_penalty_weight_sensitivity_summary()