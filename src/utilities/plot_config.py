import matplotlib.pyplot as plt

from matplotlib import colormaps
from matplotlib.colors import LinearSegmentedColormap, Normalize


SCARCITY_ORDER = ["high_scarcity", "medium_scarcity", "low_scarcity"]

SCARCITY_LABELS = {
    "high_scarcity": "High",
    "medium_scarcity": "Medium",
    "low_scarcity": "Low",
}


# =========================================================
# MODEL VISUAL STYLES
# =========================================================

MODEL_COLORS = {
    "Quantity": "#7EA6D8",
    "Quality": "#7FBE8C",
    "Aggregate-Value": "#D97A7C",
}

MODEL_HATCHES = {
    "Quantity": "///",
    "Quality": "\\\\\\",
    "Aggregate-Value": "xxx",
}


# =========================================================
# SUITABILITY VISUAL STYLES
# =========================================================

SUITABILITY_COLORS = {
    0.30: "#7EA6D8",
    0.50: "#7FBE8C",
    0.70: "#D97A7C",
}


# =========================================================
# HEATMAP VISUAL STYLE
# =========================================================

HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "heatmap_cmap",
    [
        (0.00, "#DCE8F5"),
        (0.03, "#B7D0EA"),
        (0.08, "#7EA6D8"),
        (0.20, "#7FBE8C"),
        (0.50, "#A8B980"),
        (1.00, "#D97A7C"),
    ],
)

HEATMAP_NORM = Normalize(
    vmin=0,
    vmax=5,
)


# =========================================================
# GLOBAL PLOT STYLE
# =========================================================

def apply_plot_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": [
            "Times New Roman",
            "Times",
            "DejaVu Serif",
        ],

        "font.size": 14,
        "axes.titlesize": 15,
        "axes.labelsize": 15,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 14,

        "axes.grid": True,
        "grid.linestyle": "--",
        "grid.alpha": 0.35,

        "hatch.linewidth": 0.8,

        "figure.dpi": 120,
        "savefig.dpi": 300,
    })


# =========================================================
# SCARCITY HELPERS
# =========================================================

def format_scarcity_index(df):
    df = df.reindex(SCARCITY_ORDER)
    df.index = df.index.map(SCARCITY_LABELS)

    return df


# =========================================================
# MODEL STYLE HELPERS
# =========================================================

def get_model_colors(columns):
    return [
        MODEL_COLORS[column]
        for column in columns
    ]


def get_model_hatches(columns):
    return [
        MODEL_HATCHES[column]
        for column in columns
    ]


def apply_model_hatches(
    ax,
    columns,
):
    """
    Apply model-specific hatch patterns to grouped bar charts
    so that the models remain distinguishable in black-and-white print.
    """

    hatches = get_model_hatches(
        columns
    )

    for container, hatch in zip(
        ax.containers,
        hatches,
    ):
        for patch in container:
            patch.set_hatch(
                hatch
            )

            patch.set_edgecolor(
                "black"
            )

            patch.set_linewidth(
                0.8
            )


# =========================================================
# LEGEND
# =========================================================

def apply_model_legend(ax):
    handles, labels = ax.get_legend_handles_labels()

    existing_legend = ax.get_legend()

    if existing_legend is not None:
        existing_legend.remove()

    fig = ax.get_figure()

    fig.legend(
        handles,
        labels,
        title="Model",
        loc="center right",
        bbox_to_anchor=(0.98, 0.5),
        frameon=True,
    )


# =========================================================
# SAVE
# =========================================================

def save_figure(path):
    plt.xticks(
        rotation=0
    )

    plt.tight_layout(
        rect=[0, 0, 0.90, 1]
    )

    plt.savefig(
        path,
        dpi=300,
    )

    plt.close()