import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.utilities.plot_config import (
    apply_plot_style,
    format_scarcity_index,
    apply_model_legend,
    save_figure,
    get_model_colors,
)


apply_plot_style()


ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "outputs" / "data"
FIGURE_DIR = ROOT_DIR / "outputs" / "figures"

RESOURCE_SCARCITY_CSV = DATA_DIR / "ieee33_results_one_factor_analysis.csv"

TIME_SUMMARY_CSV = DATA_DIR / "ieee33_summary_one_factor_solution_time_analysis.csv"
TIME_FIGURE = FIGURE_DIR / "ieee33_barchart_one_factor_solution_time_analysis.png"


def load_results():
    return pd.read_csv(RESOURCE_SCARCITY_CSV)


def create_time_summary(df):
    scarcity_order = ["high_scarcity", "medium_scarcity", "low_scarcity"]

    summary = (
        df.groupby("scarcity")[["qty_time", "qual_time", "w_time"]]
        .mean()
        .reindex(scarcity_order)
        .reset_index()
    )

    summary = summary.rename(
        columns={
            "qty_time": "Quantity",
            "qual_time": "Quality",
            "w_time": "Weighted",
        }
    )

    return summary

def save_time_summary(summary):
    summary.to_csv(TIME_SUMMARY_CSV, index=False)


def save_time_plot(summary):
    plot_df = summary.set_index("scarcity")
    plot_df = format_scarcity_index(plot_df)

    ax = plot_df.plot(
        kind="bar",
        figsize=(8, 5),
        color=get_model_colors(plot_df.columns),
    )

    ax.set_title("Average Solve Time by Model and Scarcity Level (IEEE 33-Bus)")
    ax.set_xlabel("Scarcity Level")
    ax.set_ylabel("Average Solve Time (seconds)")
    apply_model_legend(ax)

    save_figure(TIME_FIGURE)


def main():
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = load_results()
    summary = create_time_summary(df)

    print("\n=== AVERAGE SOLVE TIME BY SCARCITY ===")
    print(summary)

    save_time_summary(summary)
    save_time_plot(summary)

    print("\nFiles saved:")
    print(f"- {TIME_SUMMARY_CSV}")
    print(f"- {TIME_FIGURE}")


if __name__ == "__main__":
    main()