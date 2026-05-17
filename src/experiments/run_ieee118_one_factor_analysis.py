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

from src.experiments.scenario_solver import run_single_scenario


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "outputs" / "data"
FIGURE_DIR = ROOT_DIR / "outputs" / "figures"

OUTPUT_CSV = DATA_DIR / "ieee118_results_one_factor_analysis.csv"
SUMMARY_CSV = DATA_DIR / "ieee118_summary_one_factor_analysis.csv"

CRITICAL_FIG = FIGURE_DIR / "ieee118_barchart_one_factor_analysis_crtical_node_coverage_comparison.png"
VALUE_FIG = FIGURE_DIR / "ieee118_barchart_one_factor_analysis_total_value_comparison.png"


def run_experiment():
    results = []

    scarcity_levels = {
        "high_scarcity": 10,
        "medium_scarcity": 15,
        "low_scarcity": 20,
    }

    for scarcity_label, num_resources in scarcity_levels.items():
        for seed in range(30):
            res = run_single_scenario(
                seed=seed,
                network="118",
                num_resources=num_resources,
                feasibility_prob=0.45,
            )

            if res["status"] == "infeasible":
                continue

            results.append({
                "seed": seed,
                "scarcity": scarcity_label,

                # NEW
                "F": res["quantity"]["F"],
                "T_v": res["quantity"]["T_v"],

                # values
                "qty_value": res["quantity"]["value"],
                "qual_value": res["quality"]["value"],
                "w_value": res["weighted"]["value"],

                # critical
                "qty_critical": res["quantity"]["critical_covered"],
                "qual_critical": res["quality"]["critical_covered"],
                "w_critical": res["weighted"]["critical_covered"],

                # vulnerable
                "qty_vulnerable": res["quantity"]["vulnerable_covered"],
                "qual_vulnerable": res["quality"]["vulnerable_covered"],
                "w_vulnerable": res["weighted"]["vulnerable_covered"],

                # NEW
                "qty_assignments": res["quantity"]["assignments"],
                "qual_assignments": res["quality"]["assignments"],
                "w_assignments": res["weighted"]["assignments"],

                "qual_slack": res["quality"]["slack"],

                # time
                "qty_time": res["quantity"]["solve_time"],
                "qual_time": res["quality"]["solve_time"],
                "w_time": res["weighted"]["solve_time"],
            })

    return pd.DataFrame(results)


def print_summary(df):
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    summary = df.groupby("scarcity")[
        [
            "F", "T_v",

            "qty_assignments", "qual_assignments", "w_assignments",

            "qty_value", "qual_value", "w_value",
            "qty_critical", "qual_critical", "w_critical",
            "qty_vulnerable", "qual_vulnerable", "w_vulnerable",

            "qual_slack",

            "qty_time", "qual_time", "w_time",
        ]
    ].mean()

    summary = summary.reindex(
        ["high_scarcity", "medium_scarcity", "low_scarcity"]
    )

    print("\n=== IEEE118 AVERAGES BY SCARCITY ===")
    print(summary)

    return summary


def save_plots(summary):
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    critical_df = summary[
        ["qty_critical", "qual_critical", "w_critical"]
    ].rename(
        columns={
            "qty_critical": "Quantity",
            "qual_critical": "Quality",
            "w_critical": "Weighted",
        }
    )

    critical_df = format_scarcity_index(critical_df)

    ax = critical_df.plot(
    kind="bar",
    figsize=(8, 5),
    color=get_model_colors(critical_df.columns),
    )

    ax.set_title("Critical Node Coverage by Model (IEEE 118-Bus)")
    ax.set_xlabel("Scarcity Level")
    ax.set_ylabel("Average Critical Nodes Served")
    apply_model_legend(ax)

    save_figure(CRITICAL_FIG)

    value_df = summary[
        ["qty_value", "qual_value", "w_value"]
    ].rename(
        columns={
            "qty_value": "Quantity",
            "qual_value": "Quality",
            "w_value": "Weighted",
        }
    )

    value_df = format_scarcity_index(value_df)

    ax = value_df.plot(
    kind="bar",
    figsize=(8, 5),
    color=get_model_colors(value_df.columns),
    )
    
    ax.set_title("Average Total Value by Model (IEEE 118-Bus)")
    ax.set_xlabel("Scarcity Level")
    ax.set_ylabel("Average Total Value")
    apply_model_legend(ax)

    save_figure(VALUE_FIG)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = run_experiment()
    summary = print_summary(df)

    print("\n=== IEEE118 RESULTS ===")
    print(df.head())

    df.to_csv(OUTPUT_CSV, index=False)
    summary.to_csv(SUMMARY_CSV)
    save_plots(summary)

    print("\nFiles saved:")
    print(f"- {OUTPUT_CSV}")
    print(f"- {SUMMARY_CSV}")
    print(f"- {CRITICAL_FIG}")
    print(f"- {VALUE_FIG}")


if __name__ == "__main__":
    main()