import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.experiments.scenario_solver import run_single_scenario


ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "outputs" / "data"

IEEE57_TIME_CSV = DATA_DIR / "ieee57_results_time_analysis.csv"
IEEE57_TIME_SUMMARY_CSV = DATA_DIR / "ieee57_results_time_summary.csv"


def run_ieee57_time_experiment():
    results = []

    for seed in range(30):
        res = run_single_scenario(
            seed=seed,
            network="57",
            num_resources=12,
            feasibility_prob=0.45,
        )

        if res["status"] == "infeasible":
            results.append({
                "seed": seed,
                "network": "ieee57",
                "status": "infeasible",
                "qty_time": None,
                "qual_time": None,
                "w_time": None,
            })
            continue

        results.append({
            "seed": seed,
            "network": "ieee57",
            "status": "optimal",
            "qty_time": res["quantity"]["solve_time"],
            "qual_time": res["quality"]["solve_time"],
            "w_time": res["weighted"]["solve_time"],
        })

    return pd.DataFrame(results)


def create_time_summary(df):
    summary = df[["qty_time", "qual_time", "w_time"]].mean().to_frame().T

    summary = summary.rename(
        columns={
            "qty_time": "Quantity Model",
            "qual_time": "Quality Model",
            "w_time": "Weighted Model",
        }
    )

    summary.insert(0, "network", "ieee57")

    return summary


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = run_ieee57_time_experiment()
    summary = create_time_summary(df)

    print("\n=== IEEE57 TIME RESULTS ===")
    print(df)

    print("\n=== IEEE57 AVERAGE SOLVE TIME ===")
    print(summary)

    df.to_csv(IEEE57_TIME_CSV, index=False)
    summary.to_csv(IEEE57_TIME_SUMMARY_CSV, index=False)

    print("\nFiles saved:")
    print(f"- {IEEE57_TIME_CSV}")
    print(f"- {IEEE57_TIME_SUMMARY_CSV}")


if __name__ == "__main__":
    main()