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
    """Return the average assignments per secondary priority class."""

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
# SUITABILITY PROBABILITY EXPERIMENT
# =========================================================

def run_suitability_probability_experiment():
    """Run the IEEE 33-bus suitability probability experiment."""

    results = []

    suitability_levels = [0.30, 0.50, 0.70]

    # Hold the other experimental factors at their intermediate levels.
    num_resources = 7
    availability_prob = 0.45

    for suitability_prob in suitability_levels:
        for seed in range(100):
            try:
                res = run_single_scenario(
                    seed=seed,
                    network="33",
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
                        "suitability_probability": suitability_prob,
                        "status": "infeasible",

                        "quantity_assignments": None,
                        "quantity_assignment_value": None,
                        "quantity_highest_priority": None,
                        "quantity_secondary_priority": None,

                        "quality_assignments": None,
                        "quality_assignment_value": None,
                        "quality_highest_priority": None,
                        "quality_secondary_priority": None,

                        "w_assignments": None,
                        "w_assignment_value": None,
                        "w_highest_priority": None,
                        "w_secondary_priority": None,

                        "quantity_time": None,
                        "quality_time": None,
                        "w_time": None,
                    }
                )
                continue

            results.append(
                {
                    "seed": seed,
                    "suitability_probability": suitability_prob,
                    "status": "optimal",

                    "quantity_assignments":
                        res["quantity"]["assignments"],
                    "quantity_assignment_value":
                        res["quantity"]["assignment_value"],
                    "quantity_highest_priority":
                        res["quantity"]["highest_priority_covered"],
                    "quantity_secondary_priority":
                        average_secondary_priority_assignments(
                            res["quantity"]
                        ),

                    "quality_assignments":
                        res["quality"]["assignments"],
                    "quality_assignment_value":
                        res["quality"]["assignment_value"],
                    "quality_highest_priority":
                        res["quality"]["highest_priority_covered"],
                    "quality_secondary_priority":
                        average_secondary_priority_assignments(
                            res["quality"]
                        ),

                    "w_assignments":
                        res["aggregate_value"]["assignments"],
                    "w_assignment_value":
                        res["aggregate_value"]["assignment_value"],
                    "w_highest_priority":
                        res["aggregate_value"]["highest_priority_covered"],
                    "w_secondary_priority":
                        average_secondary_priority_assignments(
                            res["aggregate_value"]
                        ),

                    "quantity_time":
                        res["quantity"]["solve_time"],
                    "quality_time":
                        res["quality"]["solve_time"],
                    "w_time":
                        res["aggregate_value"]["solve_time"],
                }
            )

    return pd.DataFrame(results)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = run_suitability_probability_experiment()

    results_path = (
        DATA_DIR
        / "ieee33_suitability_probability_results.csv"
    )

    df.to_csv(
        results_path,
        index=False,
    )

    print("\nFile saved:")
    print(f" - {results_path}")