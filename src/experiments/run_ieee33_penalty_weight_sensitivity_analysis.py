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


def average_slack(formulation_result):
    """Return the average slack across secondary priority classes."""

    slack = formulation_result["slack"]

    if not slack:
        return 0.0

    return sum(slack.values()) / len(slack)


# =========================================================
# PENALTY-WEIGHT SENSITIVITY EXPERIMENT
# =========================================================

def run_penalty_weight_sensitivity_experiment():
    """Evaluate the effect of the secondary-priority penalty weight."""

    results = []

    penalty_weights = [0.25, 0.50, 1.00, 2.00]

    # Keep the other experimental factors fixed at their medium levels.
    num_resources = 7
    availability_prob = 0.45
    suitability_prob = 0.50

    for penalty_weight in penalty_weights:
        for seed in range(100):
            try:
                res = run_single_scenario(
                    seed=seed,
                    network="33",
                    num_resources=num_resources,
                    availability_prob=availability_prob,
                    suitability_prob=suitability_prob,
                    penalty_weight=penalty_weight,
                )
            finally:
                gp.disposeDefaultEnv()
                gc.collect()

            if res["status"] == "infeasible":
                results.append(
                    {
                        "seed": seed,
                        "penalty_weight": penalty_weight,
                        "status": "infeasible",

                        "quantity_assignment_value": None,
                        "quantity_highest_priority": None,
                        "quantity_secondary_priority": None,
                        "quantity_average_slack": None,

                        "quality_assignment_value": None,
                        "quality_highest_priority": None,
                        "quality_secondary_priority": None,
                        "quality_average_slack": None,

                        "aggregate_value_assignment_value": None,
                        "aggregate_value_highest_priority": None,
                        "aggregate_value_secondary_priority": None,
                    }
                )
                continue

            results.append(
                {
                    "seed": seed,
                    "penalty_weight": penalty_weight,
                    "status": "optimal",

                    "quantity_assignment_value":
                        res["quantity"]["assignment_value"],
                    "quantity_highest_priority":
                        res["quantity"]["highest_priority_covered"],
                    "quantity_secondary_priority":
                        average_secondary_priority_assignments(
                            res["quantity"]
                        ),
                    "quantity_average_slack":
                        average_slack(
                            res["quantity"]
                        ),

                    "quality_assignment_value":
                        res["quality"]["assignment_value"],
                    "quality_highest_priority":
                        res["quality"]["highest_priority_covered"],
                    "quality_secondary_priority":
                        average_secondary_priority_assignments(
                            res["quality"]
                        ),
                    "quality_average_slack":
                        average_slack(
                            res["quality"]
                        ),

                    "aggregate_value_assignment_value":
                        res["aggregate_value"]["assignment_value"],
                    "aggregate_value_highest_priority":
                        res["aggregate_value"]["highest_priority_covered"],
                    "aggregate_value_secondary_priority":
                        average_secondary_priority_assignments(
                            res["aggregate_value"]
                        ),
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

    df = run_penalty_weight_sensitivity_experiment()

    results_path = (
        DATA_DIR
        / "ieee33_penalty_weight_sensitivity_results.csv"
    )

    df.to_csv(
        results_path,
        index=False,
    )

    print("\nFile saved:")
    print(f" - {results_path}")