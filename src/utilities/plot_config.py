import matplotlib.pyplot as plt


SCARCITY_ORDER = ["high_scarcity", "medium_scarcity", "low_scarcity"]

SCARCITY_LABELS = {
    "high_scarcity": "High",
    "medium_scarcity": "Medium",
    "low_scarcity": "Low",
}

MODEL_COLORS = {
    "Quantity": "#4C72B0",
    "Quality": "#55A868",
    "Weighted": "#C44E52",
}


def apply_plot_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "axes.grid": True,
        "grid.linestyle": "--",
        "grid.alpha": 0.35,
        "figure.dpi": 120,
        "savefig.dpi": 300,
    })


def format_scarcity_index(df):
    df = df.reindex(SCARCITY_ORDER)
    df.index = df.index.map(SCARCITY_LABELS)
    return df


def get_model_colors(columns):
    return [MODEL_COLORS[column] for column in columns]


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


def save_figure(path):
    plt.xticks(rotation=0)
    plt.tight_layout(rect=[0, 0, 0.90, 1])
    plt.savefig(path, dpi=300)
    plt.close()