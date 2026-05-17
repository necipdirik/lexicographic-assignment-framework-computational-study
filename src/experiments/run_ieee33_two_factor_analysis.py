import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd
import seaborn as sns

from src.experiments.scenario_solver import run_single_scenario
from src.utilities.plot_config import apply_plot_style


apply_plot_style()


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"


SCARCITY_ORDER = ["high_scarcity", "medium_scarcity", "low_scarcity"]
FEASIBILITY_ORDER = ["high_feasibility", "medium_feasibility", "low_feasibility"]

SCARCITY_LABELS = {
    "high_scarcity": "High",
    "medium_scarcity": "Medium",
    "low_scarcity": "Low",
}

FEASIBILITY_LABELS = {
    "low_feasibility": "Low",
    "medium_feasibility": "Medium",
    "high_feasibility": "High",
}


def run_two_factor_experiment():
    results = []

    resource_levels = {
        "high_scarcity": 4,
        "medium_scarcity": 7,
        "low_scarcity": 10,
    }

    feasibility_levels = {
        "low_feasibility": 0.30,
        "medium_feasibility": 0.45,
        "high_feasibility": 0.60,
    }

    for scarcity_label, num_resources in resource_levels.items():
        for feas_label, feasibility_prob in feasibility_levels.items():
            for seed in range(100):
                res = run_single_scenario(
                    seed=seed,
                    num_resources=num_resources,
                    feasibility_prob=feasibility_prob,
                )

                if res["status"] == "infeasible":
                    results.append({
                        "seed": seed,
                        "scarcity": scarcity_label,
                        "feasibility": feas_label,
                        "num_resources": num_resources,
                        "feasibility_prob": feasibility_prob,
                        "status": "infeasible",

                        "qty_value": None,
                        "qty_critical": None,
                        "qty_vulnerable": None,

                        "qual_value": None,
                        "qual_critical": None,
                        "qual_vulnerable": None,

                        "w_value": None,
                        "w_critical": None,
                        "w_vulnerable": None,
                    })
                    continue

                results.append({
                    "seed": seed,
                    "scarcity": scarcity_label,
                    "feasibility": feas_label,
                    "num_resources": num_resources,
                    "feasibility_prob": feasibility_prob,
                    "status": "optimal",

                    "F": res["quantity"]["F"],
                    "T_v": res["quantity"]["T_v"],

                    "qty_value": res["quantity"]["value"],
                    "qty_critical": res["quantity"]["critical_covered"],
                    "qty_vulnerable": res["quantity"]["vulnerable_covered"],

                    "qual_value": res["quality"]["value"],
                    "qual_critical": res["quality"]["critical_covered"],
                    "qual_vulnerable": res["quality"]["vulnerable_covered"],

                    "w_value": res["weighted"]["value"],
                    "w_critical": res["weighted"]["critical_covered"],
                    "w_vulnerable": res["weighted"]["vulnerable_covered"],
                })

    return pd.DataFrame(results)


def print_summary(df):
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    summary_columns = [
        "F", "T_v",
        
        "qty_value", "qual_value", "w_value",
        "qty_critical", "qual_critical", "w_critical",
        "qty_vulnerable", "qual_vulnerable", "w_vulnerable",
    ]

    summary = df.groupby(["scarcity", "feasibility"])[summary_columns].mean()

    summary = summary.reindex(
        pd.MultiIndex.from_product(
            [SCARCITY_ORDER, FEASIBILITY_ORDER],
            names=["scarcity", "feasibility"],
        )
    )

    print("\n=== AVERAGES (SCARCITY × FEASIBILITY) ===")
    print(summary)


def plot_heatmap(df):
    pivot = df.pivot_table(
        values="w_critical",
        index="feasibility",
        columns="scarcity",
        aggfunc="mean",
    )

    pivot = pivot.reindex(index=FEASIBILITY_ORDER, columns=SCARCITY_ORDER)
    pivot.index = pivot.index.map(FEASIBILITY_LABELS)
    pivot.columns = pivot.columns.map(SCARCITY_LABELS)

    output_path = FIGURES_DIR / "ieee33_heatmap_two_factor_analysis_weighted_model_critical_node_coverage.png"

    ax = sns.heatmap(
        pivot,
        annot=True,
        cmap="YlOrRd",
        fmt=".2f",
        vmin=0,
        annot_kws={"size": 10},
        cbar_kws={"label": "Average Critical Nodes Served"},
    )

    cbar = ax.collections[0].colorbar
    cbar.ax.yaxis.set_label_position("left")
    cbar.ax.yaxis.tick_right()

    ax.set_title("Critical Node Coverage by Weighted Model")
    ax.set_xlabel("Scarcity Level")
    ax.set_ylabel("Feasibility Level")

    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=90)

    fig = ax.get_figure()
    fig.set_size_inches(7, 4.5)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    fig.clear()

    return output_path


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = run_two_factor_experiment()

    print_summary(df)

    results_path = DATA_DIR / "ieee33_results_two_factor_analysis.csv"
    df.to_csv(results_path, index=False)

    heatmap_path = plot_heatmap(df)

    print("\nFiles saved:")
    print(f" - {results_path}")
    print(f" - {heatmap_path}")