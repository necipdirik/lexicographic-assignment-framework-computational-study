import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from src.experiments.scenario_solver import run_single_scenario
from src.utilities.plot_config import (
    apply_plot_style,
    format_scarcity_index,
    apply_model_legend,
    save_figure,
    get_model_colors,
)


apply_plot_style()


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"


def run_resource_scarcity_experiment():
    results = []

    resource_levels = {
        "high_scarcity": 4,
        "medium_scarcity": 7,
        "low_scarcity": 10,
    }

    for scarcity_label, num_resources in resource_levels.items():
        for seed in range(100):
            res = run_single_scenario(
                seed=seed,
                num_resources=num_resources,
            )

            if res["status"] == "infeasible":
                results.append({
                    "seed": seed,
                    "scarcity": scarcity_label,
                    "num_resources": num_resources,
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

                    "qty_time": None,
                    "qual_time": None,
                    "w_time": None,
                })
                continue

            results.append({
                "seed": seed,
                "scarcity": scarcity_label,
                "num_resources": num_resources,
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

                "qty_assignments": res["quantity"]["assignments"],
                "qual_assignments": res["quality"]["assignments"],
                "w_assignments": res["weighted"]["assignments"],

                "qual_slack": res["quality"]["slack"],

                "qty_time": res["quantity"]["solve_time"],
                "qual_time": res["quality"]["solve_time"],
                "w_time": res["weighted"]["solve_time"],
            })

    return pd.DataFrame(results)


def print_summary(df):
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    summary_columns = [
        "F", "T_v",

        "qty_assignments", "qual_assignments", "w_assignments",

        "qty_value", "qual_value", "w_value",
        "qty_critical", "qual_critical", "w_critical",
        "qty_vulnerable", "qual_vulnerable", "w_vulnerable",

        "qual_slack",

        "qty_time", "qual_time", "w_time",
    ]

    print("\n=== AVERAGES BY SCARCITY ===")
    scarcity_order = ["high_scarcity", "medium_scarcity", "low_scarcity"]

    summary = df.groupby("scarcity")[summary_columns].mean()
    summary = summary.reindex(scarcity_order)

    print(summary)


def save_bar_charts(df):
    grouped = df.groupby("scarcity").mean(numeric_only=True)
    grouped = format_scarcity_index(grouped)

    chart_specs = [
        (
            ["qty_value", "qual_value", "w_value"],
            "Average Total Value by Model and Scarcity Level",
            "Average Total Value",
            "ieee33_barchart_one_factor_analysis_total_value_comparison.png",
        ),
        (
            ["qty_critical", "qual_critical", "w_critical"],
            "Critical Node Coverage Comparison by Model and Scarcity Level",
            "Average Critical Nodes Served",
            "ieee33_barchart_one_factor_analysis_critical_node_coverage_comparison.png",
        ),
        (
            ["qty_vulnerable", "qual_vulnerable", "w_vulnerable"],
            "Vulnerable Node Coverage Comparison by Model and Scarcity Level",
            "Average Vulnerable Nodes Served",
            "ieee33_barchart_one_factor_analysis_vulnerable_node_coverage_comparison.png",
        ),
    ]

    saved_paths = []

    for columns, title, ylabel, filename in chart_specs:
        output_path = FIGURES_DIR / filename

        plot_df = grouped[columns].rename(
            columns={
                columns[0]: "Quantity",
                columns[1]: "Quality",
                columns[2]: "Weighted",
            }
        )

        ax = plot_df.plot(
            kind="bar",
            figsize=(8, 5),
            color=get_model_colors(plot_df.columns),
        )

        ax.set_title(title)
        ax.set_xlabel("Scarcity Level")
        ax.set_ylabel(ylabel)
        apply_model_legend(ax)

        save_figure(output_path)
        saved_paths.append(output_path)

    return saved_paths


def save_boxplots(df):
    boxplot_specs = [
        (
            "w_vulnerable",
            "Distribution of Vulnerable Coverage byWeighted Model",
            "Vulnerable Nodes Served",
            "ieee33_boxplot_one_factor_analysis_weighted_model_vulnerable_node_coverage.png",
        ),
        (
            "w_critical",
            "Distribution of Critical Coverage by Weighted Model",
            "Critical Nodes Served",
            "ieee33_boxplot_one_factor_analysis_weighted_model_critical_node_coverage.png",
        ),
    ]

    saved_paths = []

    plot_df = df.copy()
    plot_df["scarcity"] = pd.Categorical(
        plot_df["scarcity"],
        categories=["high_scarcity", "medium_scarcity", "low_scarcity"],
        ordered=True,
    )
    plot_df["scarcity_label"] = plot_df["scarcity"].map({
        "high_scarcity": "High",
        "medium_scarcity": "Medium",
        "low_scarcity": "Low",
    })

    for y_column, title, ylabel, filename in boxplot_specs:
        output_path = FIGURES_DIR / filename

        fig, ax = plt.subplots(figsize=(8, 5))

        sns.boxplot(
            data=plot_df,
            x="scarcity_label",
            y=y_column,
            ax=ax,
        )

        ax.set_title(title)
        ax.set_xlabel("Scarcity Level")
        ax.set_ylabel(ylabel)

        save_figure(output_path)
        saved_paths.append(output_path)

    return saved_paths


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = run_resource_scarcity_experiment()

    print_summary(df)

    results_path = DATA_DIR / "ieee33_results_one_factor_analysis.csv"
    df.to_csv(results_path, index=False)

    bar_chart_paths = save_bar_charts(df)
    boxplot_paths = save_boxplots(df)

    print("\nFiles saved:")
    print(f" - {results_path}")

    for path in bar_chart_paths + boxplot_paths:
        print(f" - {path}")