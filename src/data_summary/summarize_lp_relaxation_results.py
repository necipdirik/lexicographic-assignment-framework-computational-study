import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"


# =========================================================
# LP-RELAXATION SUMMARY
# =========================================================

def create_lp_relaxation_summary(
    df,
    network_name,
):
    """
    Create LP-relaxation integrality statistics.
    """

    tested = len(df)

    overlapping = int(
        df[
            "secondary_classes_overlap"
        ].sum()
    )

    quantity_fractional = int(
        (
            ~df[
                "quantity_integral"
            ]
        ).sum()
    )

    quality_fractional = int(
        (
            ~df[
                "quality_integral"
            ]
        ).sum()
    )

    quantity_max_fractionality = (
        df[
            "quantity_maximum_fractionality"
        ].max()
    )

    quality_max_fractionality = (
        df[
            "quality_maximum_fractionality"
        ].max()
    )

    summary = {
        "network": network_name,
        "scenarios_tested": tested,
        "overlapping_secondary_classes": overlapping,
        "quantity_fractional_scenarios": quantity_fractional,
        "quality_fractional_scenarios": quality_fractional,
        "quantity_maximum_fractionality":
            quantity_max_fractionality,
        "quality_maximum_fractionality":
            quality_max_fractionality,
        "quantity_fractional_percentage":
            (
                100 * quantity_fractional / tested
                if tested > 0
                else 0.0
            ),
        "quality_fractional_percentage":
            (
                100 * quality_fractional / tested
                if tested > 0
                else 0.0
            ),
    }

    return summary


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    ieee33_path = (
        DATA_DIR
        / "ieee33_lp_relaxation_results.csv"
    )

    ieee118_path = (
        DATA_DIR
        / "ieee118_lp_relaxation_results.csv"
    )

    ieee33_df = pd.read_csv(
        ieee33_path
    )

    ieee118_df = pd.read_csv(
        ieee118_path
    )

    summaries = [
        create_lp_relaxation_summary(
            ieee33_df,
            "IEEE 33-BUS",
        ),
        create_lp_relaxation_summary(
            ieee118_df,
            "IEEE 118-BUS",
        ),
    ]

    summary_df = pd.DataFrame(
        summaries
    )

    output_path = (
        DATA_DIR
        / "lp_relaxation_summary.csv"
    )

    summary_df.to_csv(
        output_path,
        index=False,
    )

    print(
        "\n=== LP-RELAXATION SUMMARY ==="
    )

    print(
        summary_df.to_string(
            index=False
        )
    )

    print("\nFile saved:")
    print(f" - {output_path}")