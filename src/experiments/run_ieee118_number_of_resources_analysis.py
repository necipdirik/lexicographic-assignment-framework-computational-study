import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import gc

import gurobipy as gp
import pandas as pd

from src.experiments.scenario_solver import run_single_scenario


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def average_secondary_priority_assignments(formulation_result):
    """
    Return the average number of assignments across
    secondary-priority classes.
    """

    secondary_priority_covered = formulation_result[
        "secondary_priority_covered"
    ]

    if not secondary_priority_covered:
        return 0.0

    return (
        sum(secondary_priority_covered.values())
        / len(secondary_priority_covered)
    )


# =========================================================
# NUMBER OF RESOURCES EXPERIMENT
# =========================================================

def run_number_of_resources_experiment():
    """
    Run the IEEE 118-bus larger-scale validation experiment
    for different numbers of resources.
    """

    results = []

    resource_levels = [
        10,
        15,
        20,
    ]

    # Hold the remaining experimental factors
    # at their medium levels.
    availability_prob = 0.45
    suitability_prob = 0.50

    for num_resources in resource_levels:
        for seed in range(100):

            try:
                res = run_single_scenario(
                    seed=seed,
                    network="118",
                    num_resources=num_resources,
                    availability_prob=availability_prob,
                    suitability_prob=suitability_prob,
                )
            finally:
                gp.disposeDefaultEnv()
                gc.collect()

            if res["status"] == "infeasible":
                results.append(
                    {
                        "seed": seed,
                        "num_resources": num_resources,
                        "availability_probability":
                            availability_prob,
                        "suitability_probability":
                            suitability_prob,
                        "status": "infeasible",

                        "qty_assignments": None,
                        "qty_assignment_value": None,
                        "qty_highest_priority": None,
                        "qty_secondary_priority": None,

                        "qual_assignments": None,
                        "qual_assignment_value": None,
                        "qual_highest_priority": None,
                        "qual_secondary_priority": None,

                        "w_assignments": None,
                        "w_assignment_value": None,
                        "w_highest_priority": None,
                        "w_secondary_priority": None,

                        "qty_time": None,
                        "qual_time": None,
                        "w_time": None,
                    }
                )

                continue

            results.append(
                {
                    "seed": seed,
                    "num_resources": num_resources,
                    "availability_probability":
                        availability_prob,
                    "suitability_probability":
                        suitability_prob,
                    "status": "optimal",

                    "qty_assignments":
                        res["quantity"]["assignments"],
                    "qty_assignment_value":
                        res["quantity"]["assignment_value"],
                    "qty_highest_priority":
                        res["quantity"][
                            "highest_priority_covered"
                        ],
                    "qty_secondary_priority":
                        average_secondary_priority_assignments(
                            res["quantity"]
                        ),

                    "qual_assignments":
                        res["quality"]["assignments"],
                    "qual_assignment_value":
                        res["quality"]["assignment_value"],
                    "qual_highest_priority":
                        res["quality"][
                            "highest_priority_covered"
                        ],
                    "qual_secondary_priority":
                        average_secondary_priority_assignments(
                            res["quality"]
                        ),

                    "w_assignments":
                        res["weighted"]["assignments"],
                    "w_assignment_value":
                        res["weighted"]["assignment_value"],
                    "w_highest_priority":
                        res["weighted"][
                            "highest_priority_covered"
                        ],
                    "w_secondary_priority":
                        average_secondary_priority_assignments(
                            res["weighted"]
                        ),

                    "qty_time":
                        res["quantity"]["solve_time"],
                    "qual_time":
                        res["quality"]["solve_time"],
                    "w_time":
                        res["weighted"]["solve_time"],
                }
            )

    return pd.DataFrame(results)


# =========================================================
# SUMMARY
# =========================================================

def print_summary(df):
    """
    Print average IEEE 118-bus results
    by number of resources.
    """

    pd.set_option(
        "display.max_columns",
        None,
    )

    pd.set_option(
        "display.width",
        220,
    )

    summary_columns = [
        "qty_assignments",
        "qual_assignments",
        "w_assignments",

        "qty_assignment_value",
        "qual_assignment_value",
        "w_assignment_value",

        "qty_highest_priority",
        "qual_highest_priority",
        "w_highest_priority",

        "qty_secondary_priority",
        "qual_secondary_priority",
        "w_secondary_priority",

        "qty_time",
        "qual_time",
        "w_time",
    ]

    print(
        "\n=== IEEE 118-BUS AVERAGES "
        "BY NUMBER OF RESOURCES ==="
    )

    summary = (
        df.groupby(
            "num_resources"
        )[summary_columns]
        .mean()
        .reindex(
            [
                10,
                15,
                20,
            ]
        )
    )

    print(summary)

    return summary


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = run_number_of_resources_experiment()

    summary = print_summary(df)

    results_path = (
        DATA_DIR
        / "ieee118_number_of_resources_results.csv"
    )

    summary_path = (
        DATA_DIR
        / "ieee118_number_of_resources_summary.csv"
    )

    df.to_csv(
        results_path,
        index=False,
    )

    summary.to_csv(
        summary_path,
    )

    print("\nFiles saved:")
    print(f" - {results_path}")
    print(f" - {summary_path}")