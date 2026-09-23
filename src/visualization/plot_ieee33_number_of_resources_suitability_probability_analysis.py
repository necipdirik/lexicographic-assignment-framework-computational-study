import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import pandas as pd

from src.utilities.plot_config import (
    apply_plot_style,
    HEATMAP_CMAP,
    HEATMAP_NORM,
)


apply_plot_style()


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"


# =========================================================
# DATA
# =========================================================

def load_summary():
    """Load the IEEE 33-bus two-factor summary."""

    summary_path = (
        DATA_DIR
        / (
            "ieee33_number_of_resources_"
            "suitability_probability_summary.csv"
        )
    )

    return pd.read_csv(
        summary_path
    )


# =========================================================
# FIGURE
# =========================================================

def save_highest_priority_heatmaps(summary):
    """
    Generate three heatmaps showing average highest-priority
    assignments for the Quantity, Quality, and Aggregate-Value
    formulations.
    """

    formulation_specs = [
        ("qty_highest_priority", "(a) QNTF"),
        ("qual_highest_priority", "(b) QLTF"),
        ("w_highest_priority", "(c) AVF"),
    ]

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(12, 4.8),
        sharey=True,
    )

    image = None

    for ax, (column, formulation_name) in zip(
        axes,
        formulation_specs,
    ):
        heatmap_data = (
            summary.pivot(
                index="suitability_probability",
                columns="num_resources",
                values=column,
            )
            .reindex(
                index=[0.70, 0.50, 0.30],
                columns=[4, 7, 10],
            )
        )

        image = ax.imshow(
            heatmap_data.values,
            cmap=HEATMAP_CMAP,
            norm=HEATMAP_NORM,
            aspect="auto",
        )

        ax.set_title(
            formulation_name,
            pad=14,
        )

        ax.set_xlabel(
            "Number of Resources"
        )

        ax.set_xticks(
            range(
                len(heatmap_data.columns)
            )
        )

        ax.set_xticklabels(
            [
                str(value)
                for value in heatmap_data.columns
            ]
        )

        ax.set_yticks(
            range(
                len(heatmap_data.index)
            )
        )

        ax.set_yticklabels(
            [
                f"{value:.2f}"
                for value in heatmap_data.index
            ]
        )

        # Add visible cell boundaries for improved
        # readability in black-and-white print.
        ax.set_xticks(
            [
                value - 0.5
                for value in range(
                    1,
                    len(heatmap_data.columns)
                )
            ],
            minor=True,
        )

        ax.set_yticks(
            [
                value - 0.5
                for value in range(
                    1,
                    len(heatmap_data.index)
                )
            ],
            minor=True,
        )

        ax.grid(
            which="major",
            visible=False,
        )

        ax.grid(
            which="minor",
            color="black",
            linewidth=0.5,
            linestyle="-",
            alpha=0.4,
        )

        ax.tick_params(
            which="minor",
            bottom=False,
            left=False,
        )

        # Display the numerical value in each cell.
        for row_index in range(
            len(heatmap_data.index)
        ):
            for column_index in range(
                len(heatmap_data.columns)
            ):
                value = heatmap_data.iloc[
                    row_index,
                    column_index,
                ]

                ax.text(
                    column_index,
                    row_index,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    color="black",
                    fontsize=14,
                )

    axes[0].set_ylabel(
        "Suitability Probability"
    )

    fig.subplots_adjust(
        left=0.08,
        right=0.88,
        bottom=0.15,
        top=0.84,
        wspace=0.28,
    )

    colorbar_ax = fig.add_axes(
        [0.94, 0.18, 0.015, 0.62]
    )

    colorbar = fig.colorbar(
        image,
        cax=colorbar_ax,
    )

    colorbar.set_label(
        "Average HP Assignments",
        fontsize=15,
        labelpad=25,
    )

    colorbar.ax.yaxis.set_label_position(
        "left"
    )

    colorbar.ax.tick_params(
        labelsize=14,
    )

    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        FIGURES_DIR
        / (
            "ieee33_number_of_resources_"
            "suitability_probability_"
            "highest_priority_assignments.png"
        )
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

    heatmap_path = (
        save_highest_priority_heatmaps(
            summary
        )
    )

    print("\nFigure saved:")
    print(f" - {heatmap_path}")