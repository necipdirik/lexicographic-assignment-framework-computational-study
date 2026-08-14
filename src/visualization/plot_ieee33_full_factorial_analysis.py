import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from matplotlib.patches import Patch

from src.utilities.plot_config import (
    apply_plot_style,
    SUITABILITY_COLORS,
)


apply_plot_style()

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"


# =========================================================
# DATA
# =========================================================

def load_summary():
    """Load the IEEE 33-bus full-factorial summary."""

    summary_path = (
        DATA_DIR
        / "ieee33_full_factorial_summary.csv"
    )

    return pd.read_csv(
        summary_path
    )


# =========================================================
# FULL-FACTORIAL 3D FIGURE
# =========================================================

def save_highest_priority_full_factorial_3d_figure(summary):
    """
    Generate three 3D surface plots showing average highest-priority
    assignments across the full-factorial experimental design.
    """

    formulation_specs = [
        (
            "qty_highest_priority",
            "(a) Quantity",
        ),
        (
            "qual_highest_priority",
            "(b) Quality",
        ),
        (
            "w_highest_priority",
            "(c) Aggregate-Value",
        ),
    ]

    resource_levels = np.array(
        [
            4,
            7,
            10,
        ]
    )

    availability_levels = np.array(
        [
            0.30,
            0.45,
            0.60,
        ]
    )

    suitability_levels = [
        0.30,
        0.50,
        0.70,
    ]

    X, Y = np.meshgrid(
        resource_levels,
        availability_levels,
    )

    fig = plt.figure(
        figsize=(16, 6.2)
    )

    # -----------------------------------------------------
    # PANEL POSITIONS
    # -----------------------------------------------------

    panel_positions = [
        [0.050, 0.24, 0.245, 0.64],
        [0.350, 0.24, 0.245, 0.64],
        [0.650, 0.24, 0.245, 0.64],
    ]

    for panel_index, (
        result_column,
        formulation_name,
    ) in enumerate(formulation_specs):

        ax = fig.add_axes(
            panel_positions[panel_index],
            projection="3d",
        )

        for suitability_prob in suitability_levels:

            subset = summary[
                summary["suitability_probability"]
                == suitability_prob
            ]

            pivot_table = (
                subset.pivot(
                    index="availability_probability",
                    columns="num_resources",
                    values=result_column,
                )
                .reindex(
                    index=availability_levels,
                    columns=resource_levels,
                )
            )

            Z = pivot_table.values

            ax.plot_surface(
                X,
                Y,
                Z,
                color=SUITABILITY_COLORS[
                    suitability_prob
                ],
                alpha=1,
                linewidth=0.8,
                edgecolor="black",
                antialiased=True,
                shade=False,
            )

        # -------------------------------------------------
        # PANEL TITLE
        # -------------------------------------------------

        ax.set_title(
            formulation_name,
            fontsize=17,
            pad=-2,
        )

        # -------------------------------------------------
        # AXIS LABELS
        # -------------------------------------------------

        ax.set_xlabel(
            "Number of\nResources",
            fontsize=16,
            labelpad=10,
        )

        ax.set_ylabel(
            "Availability\nProbability",
            fontsize=16,
            labelpad=12,
        )

        ax.set_zlabel("")

        # -------------------------------------------------
        # TICKS AND LIMITS
        # -------------------------------------------------

        ax.set_xticks(
            resource_levels
        )

        ax.set_yticks(
            availability_levels
        )

        ax.set_zlim(
            0,
            5,
        )

        ax.set_zticks(
            [
                0,
                1,
                2,
                3,
                4,
                5,
            ]
        )

        ax.tick_params(
            axis="x",
            labelsize=14,
            pad=2,
        )

        ax.tick_params(
            axis="y",
            labelsize=14,
            pad=2,
        )

        ax.tick_params(
            axis="z",
            labelsize=14,
            pad=2,
        )

        # -------------------------------------------------
        # VIEW
        # -------------------------------------------------

        ax.view_init(
            elev=25,
            azim=-55,
        )


    # =====================================================
    # Z-AXIS LABEL FOR LAST PANEL
    # =====================================================

    fig.text(
        0.925,
        0.60,
        "Average\nHighest-Priority Assignments",
        rotation=90,
        va="center",
        ha="center",
        multialignment="center",
        fontsize=16,
    )


    # =====================================================
    # COMMON LEGEND
    # =====================================================

    legend_handles = [
        Patch(
            facecolor=SUITABILITY_COLORS[0.30],
            edgecolor="black",
            alpha=1,
            label="Suitability Probability 0.30",
        ),
        Patch(
            facecolor=SUITABILITY_COLORS[0.50],
            edgecolor="black",
            alpha=1,
            label="Suitability Probability 0.50",
        ),
        Patch(
            facecolor=SUITABILITY_COLORS[0.70],
            edgecolor="black",
            alpha=1,
            label="Suitability Probability 0.70",
        ),
    ]

    fig.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.035),
        fontsize=15,
    )


    # =====================================================
    # SAVE
    # =====================================================

    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        FIGURES_DIR
        / (
            "ieee33_full_factorial_"
            "highest_priority_assignments_3d.png"
        )
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.35,
    )

    plt.close(fig)

    return output_path


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    summary = load_summary()

    figure_path = (
        save_highest_priority_full_factorial_3d_figure(
            summary
        )
    )

    print("\nFigure saved:")
    print(f" - {figure_path}")