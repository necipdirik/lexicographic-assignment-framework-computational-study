import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import pandas as pd

from src.utilities.plot_config import (
    apply_plot_style,
    apply_model_hatches,
    get_model_colors,
)


apply_plot_style()


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"


# =========================================================
# DATA
# =========================================================

def load_summary():
    """Load the IEEE 33-bus number-of-resources summary."""

    summary_path = (
        DATA_DIR
        / "ieee33_number_of_resources_summary.csv"
    )

    df = pd.read_csv(summary_path)

    return df.set_index("num_resources").reindex(
        [4, 7, 10]
    )


# =========================================================
# PANEL FIGURE
# =========================================================

def save_panel_figure(summary):
    """Generate a three-panel IEEE 33-bus number-of-resources figure."""

    panel_specs = [
        (
            [
                "quantity_highest_priority",
                "quality_highest_priority",
                "aggregate_value_highest_priority",
            ],
            "(a) HP Assignments",
            "Average",
        ),
        (
            [
                "quantity_secondary_priority",
                "quality_secondary_priority",
                "aggregate_value_secondary_priority",
            ],
            "(b) SP Assignments",
            "Average per Class",
        ),
        (
            [
                "quantity_assignment_value",
                "quality_assignment_value",
                "aggregate_value_assignment_value",
            ],
            "(c) Total Assignment Value",
            "Average",
        ),
    ]

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(12, 4.8),
    )

    for ax, (columns, title, ylabel) in zip(
        axes,
        panel_specs,
    ):
        plot_df = summary[columns].rename(  
            columns={
                columns[0]: "QNTF",
                columns[1]: "QLTF",
                columns[2]: "AVF",
            }
        )

        plot_df.plot(
            kind="bar",
            ax=ax,
            color=get_model_colors(plot_df.columns),
            legend=False,
        )

        apply_model_hatches(
            ax,
            plot_df.columns,
        )

        ax.set_title(title)
        ax.set_xlabel("Number of Resources")
        ax.set_ylabel(ylabel)

        ax.tick_params(
            axis="x",
            rotation=0,
        )

    # Use one common legend for the complete figure.
    handles, labels = axes[0].get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.02),
        fontsize=16,
    )

    output_path = (
        FIGURES_DIR
        / "ieee33_number_of_resources_performance.png"
    )

    fig.subplots_adjust(
        left=0.06,
        right=0.99,
        bottom=0.16,
        top=0.82,
        wspace=0.32,
    )

    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)

    return output_path


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    summary = load_summary()

    figure_path = save_panel_figure(
        summary
    )

    print("\nFigure saved:")
    print(f" - {figure_path}")