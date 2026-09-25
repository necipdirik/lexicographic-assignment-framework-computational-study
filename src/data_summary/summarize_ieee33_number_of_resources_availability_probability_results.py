import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"


# =========================================================
# TWO-FACTOR DATA SUMMARY
# =========================================================

def create_number_of_resources_availability_probability_summary():
    """
    Calculate mean IEEE 33-bus results by number of resources and 
    availability probability.
    """

    input_path = (
        DATA_DIR
        / (
            "ieee33_number_of_resources_"
            "availability_probability_results.csv"
        )
    )

    output_path = (
        DATA_DIR
        / (
            "ieee33_number_of_resources_"
            "availability_probability_summary.csv"
        )
    )

    df = pd.read_csv(input_path)

    summary_columns = [
        "qty_assignments",
        "qual_assignments",
        "w_assignments",

        "qty_assignment_value",
        "qual_assignment_value",
        "w_assignment_value",

        "qty_highest_priority",
        "qual_highest_priority",
        "w_highest_priority",

        "qty_secondary_priority",
        "qual_secondary_priority",
        "w_secondary_priority",

        "qty_time",
        "qual_time",
        "w_time",
    ]

    summary = (
        df.groupby(
            [
                "num_resources",
                "availability_probability",
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
        "\n=== IEEE 33-BUS AVERAGES BY NUMBER OF RESOURCES "
        "AND AVAILABILITY PROBABILITY ==="
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
    create_number_of_resources_availability_probability_summary()