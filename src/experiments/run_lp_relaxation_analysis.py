import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import gc
import random

import gurobipy as gp
from gurobipy import GRB
import pandas as pd

from src.experiments.scenario_solver import (
    load_ieee33_data,
    load_ieee118_data,
    generate_scenario,
    add_assignment_constraints,
    solve_subproblem_1,
    solve_subproblem_2,
    solve_quantity_formulation,
)


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "outputs" / "data"


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def classes_overlap(C, class_nodes):
    """
    Return True if any pair of secondary-priority
    classes overlaps.
    """

    for i, c1 in enumerate(C):
        for c2 in C[i + 1:]:
            if class_nodes[c1].intersection(
                class_nodes[c2]
            ):
                return True

    return False


def calculate_fractionality(
    x,
    available_pairs,
    tolerance=1e-6,
):
    """
    Calculate fractionality statistics for the
    assignment variables.

    For a variable x in [0, 1], fractionality is
    min(x, 1-x).
    """

    fractionalities = []

    for r, n in available_pairs:
        value = x[r, n].X

        fractionality = min(
            abs(value),
            abs(1.0 - value),
        )

        fractionalities.append(
            fractionality
        )

    if not fractionalities:
        return {
            "is_integral": True,
            "fractional_variable_count": 0,
            "maximum_fractionality": 0.0,
        }

    maximum_fractionality = max(
        fractionalities
    )

    fractional_variable_count = sum(
        value > tolerance
        for value in fractionalities
    )

    return {
        "is_integral":
            fractional_variable_count == 0,

        "fractional_variable_count":
            fractional_variable_count,

        "maximum_fractionality":
            maximum_fractionality,
    }


def create_assignment_value(
    R,
    N,
    C,
    class_nodes,
    available_pairs,
    seed,
    suitability_prob,
):
    """
    Construct assignment-value coefficients using
    the same procedure as scenario_solver.py.
    """

    suitability_rng = random.Random(
        seed + 1
    )

    suitability = {
        (r, n): int(
            suitability_rng.random()
            < suitability_prob
        )
        for r in R
        for n in N
    }

    assignment_value = {
        (r, n): (
            sum(
                1
                for c in C
                if n in class_nodes[c]
            )
            + suitability[r, n]
            + 1
        )
        for r, n in available_pairs
    }

    return assignment_value


# =========================================================
# QUANTITY LP RELAXATION
# =========================================================

def solve_quantity_lp_relaxation(
    R,
    N,
    available_pairs,
    H,
    C,
    class_nodes,
    M_H,
    M_c,
    penalty_weights,
):
    """
    Solve the LP relaxation of the Quantity
    formulation.
    """

    model = gp.Model(
        "quantity_lp_relaxation"
    )

    model.Params.OutputFlag = 0

    x = model.addVars(
        available_pairs,
        lb=0.0,
        ub=1.0,
        vtype=GRB.CONTINUOUS,
        name="x",
    )

    epsilon = model.addVars(
        C,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="epsilon",
    )

    add_assignment_constraints(
        model,
        x,
        available_pairs,
        R,
        N,
    )

    model.addConstr(
        gp.quicksum(
            x[r, n]
            for r, n in available_pairs
            if n in H
        )
        >= M_H,
        name="highest_priority_protection",
    )

    for c in C:
        model.addConstr(
            gp.quicksum(
                x[r, n]
                for r, n in available_pairs
                if n in class_nodes[c]
            )
            + epsilon[c]
            >= M_c[c],
            name=(
                "secondary_priority_"
                f"protection_{c}"
            ),
        )

    model.setObjective(
        gp.quicksum(
            x[r, n]
            for r, n in available_pairs
        )
        - gp.quicksum(
            penalty_weights[c] * epsilon[c]
            for c in C
        ),
        GRB.MAXIMIZE,
    )

    model.optimize()

    if model.Status != GRB.OPTIMAL:
        model.dispose()
        return None

    fractionality = calculate_fractionality(
        x,
        available_pairs,
    )

    result = {
        "objective_value":
            model.ObjVal,
        **fractionality,
    }

    model.dispose()

    return result


# =========================================================
# QUALITY LP RELAXATION
# =========================================================

def solve_quality_lp_relaxation(
    R,
    N,
    available_pairs,
    assignment_value,
    H,
    C,
    class_nodes,
    M_H,
    M_c,
    maximum_assignments,
    penalty_weights,
):
    """
    Solve the LP relaxation of the Quality
    formulation.
    """

    model = gp.Model(
        "quality_lp_relaxation"
    )

    model.Params.OutputFlag = 0

    x = model.addVars(
        available_pairs,
        lb=0.0,
        ub=1.0,
        vtype=GRB.CONTINUOUS,
        name="x",
    )

    epsilon = model.addVars(
        C,
        lb=0.0,
        vtype=GRB.CONTINUOUS,
        name="epsilon",
    )

    add_assignment_constraints(
        model,
        x,
        available_pairs,
        R,
        N,
    )

    model.addConstr(
        gp.quicksum(
            x[r, n]
            for r, n in available_pairs
        )
        == maximum_assignments,
        name="maximum_assignment_count",
    )

    model.addConstr(
        gp.quicksum(
            x[r, n]
            for r, n in available_pairs
            if n in H
        )
        >= M_H,
        name="highest_priority_protection",
    )

    for c in C:
        model.addConstr(
            gp.quicksum(
                x[r, n]
                for r, n in available_pairs
                if n in class_nodes[c]
            )
            + epsilon[c]
            >= M_c[c],
            name=(
                "secondary_priority_"
                f"protection_{c}"
            ),
        )

    model.setObjective(
        gp.quicksum(
            assignment_value[r, n]
            * x[r, n]
            for r, n in available_pairs
        )
        - gp.quicksum(
            penalty_weights[c] * epsilon[c]
            for c in C
        ),
        GRB.MAXIMIZE,
    )

    model.optimize()

    if model.Status != GRB.OPTIMAL:
        model.dispose()
        return None

    fractionality = calculate_fractionality(
        x,
        available_pairs,
    )

    result = {
        "objective_value":
            model.ObjVal,
        **fractionality,
    }

    model.dispose()

    return result


# =========================================================
# SINGLE LP-RELAXATION SCENARIO
# =========================================================

def run_lp_relaxation_scenario(
    seed,
    network,
    num_resources,
    availability_prob,
    suitability_prob,
    highest_priority_count=5,
    secondary_class_counts=None,
    penalty_weight=0.5,
):
    """
    Run the Quantity and Quality LP relaxations for
    one generated scenario.
    """

    if network == "33":
        N = load_ieee33_data()

    elif network == "118":
        N = load_ieee118_data()

    else:
        raise ValueError(
            f"Unsupported network: {network}"
        )

    (
        R,
        H,
        C,
        class_nodes,
        available_pairs,
    ) = generate_scenario(
        N,
        seed=seed,
        num_resources=num_resources,
        highest_priority_count=
            highest_priority_count,
        secondary_class_counts=
            secondary_class_counts,
        availability_prob=
            availability_prob,
    )

    overlap = classes_overlap(
        C,
        class_nodes,
    )

    assignment_value = create_assignment_value(
        R,
        N,
        C,
        class_nodes,
        available_pairs,
        seed,
        suitability_prob,
    )

    penalty_weights = {
        c: penalty_weight
        for c in C
    }

    # -----------------------------------------------------
    # Generate the original integer protection targets.
    # -----------------------------------------------------

    M_H = solve_subproblem_1(
        R,
        N,
        available_pairs,
        H,
    )

    M_c = solve_subproblem_2(
        R,
        N,
        available_pairs,
        C,
        class_nodes,
    )

    if M_H is None or M_c is None:
        return None

    # -----------------------------------------------------
    # Solve the ORIGINAL INTEGER Quantity formulation.
    #
    # The resulting assignment count is the same quantity
    # passed to the Quality formulation in the original
    # sequential framework.
    # -----------------------------------------------------

    integer_quantity = (
        solve_quantity_formulation(
            R,
            N,
            available_pairs,
            assignment_value,
            H,
            C,
            class_nodes,
            M_H,
            M_c,
            penalty_weights,
        )
    )

    if integer_quantity is None:
        return None

    maximum_assignments = (
        integer_quantity["assignments"]
    )

    # -----------------------------------------------------
    # Quantity LP relaxation
    # -----------------------------------------------------

    quantity_lp = (
        solve_quantity_lp_relaxation(
            R,
            N,
            available_pairs,
            H,
            C,
            class_nodes,
            M_H,
            M_c,
            penalty_weights,
        )
    )

    if quantity_lp is None:
        return None

    # -----------------------------------------------------
    # Quality LP relaxation
    # -----------------------------------------------------

    quality_lp = (
        solve_quality_lp_relaxation(
            R,
            N,
            available_pairs,
            assignment_value,
            H,
            C,
            class_nodes,
            M_H,
            M_c,
            maximum_assignments,
            penalty_weights,
        )
    )

    if quality_lp is None:
        return None

    return {
        "seed":
            seed,

        "network":
            network,

        "num_resources":
            num_resources,

        "availability_probability":
            availability_prob,

        "suitability_probability":
            suitability_prob,

        "secondary_classes_overlap":
            overlap,

        "maximum_assignments":
            maximum_assignments,

        "quantity_integral":
            quantity_lp[
                "is_integral"
            ],

        "quantity_fractional_variable_count":
            quantity_lp[
                "fractional_variable_count"
            ],

        "quantity_maximum_fractionality":
            quantity_lp[
                "maximum_fractionality"
            ],

        "quality_integral":
            quality_lp[
                "is_integral"
            ],

        "quality_fractional_variable_count":
            quality_lp[
                "fractional_variable_count"
            ],

        "quality_maximum_fractionality":
            quality_lp[
                "maximum_fractionality"
            ],
    }


# =========================================================
# IEEE 33 FULL-FACTORIAL ANALYSIS
# =========================================================

def run_ieee33_lp_analysis():
    """
    Run LP-relaxation analysis across the complete
    IEEE 33-bus full-factorial design.
    """

    results = []

    resource_levels = [
        4,
        7,
        10,
    ]

    availability_levels = [
        0.30,
        0.45,
        0.60,
    ]

    suitability_levels = [
        0.30,
        0.50,
        0.70,
    ]

    total = (
        len(resource_levels)
        * len(availability_levels)
        * len(suitability_levels)
        * 100
    )

    counter = 0

    print(
        "\n=== IEEE 33-BUS "
        "LP-RELAXATION ANALYSIS ==="
    )

    for num_resources in resource_levels:
        for availability_prob in availability_levels:
            for suitability_prob in suitability_levels:
                for seed in range(100):

                    counter += 1

                    result = (
                        run_lp_relaxation_scenario(
                            seed=seed,
                            network="33",
                            num_resources=
                                num_resources,
                            availability_prob=
                                availability_prob,
                            suitability_prob=
                                suitability_prob,
                        )
                    )

                    if result is not None:
                        results.append(
                            result
                        )

                    if counter % 100 == 0:
                        print(
                            "IEEE 33 progress: "
                            f"{counter}/{total}"
                        )

                    gp.disposeDefaultEnv()
                    gc.collect()

    return pd.DataFrame(
        results
    )


# =========================================================
# IEEE 118 ANALYSIS
# =========================================================

def run_ieee118_lp_analysis():
    """
    Run LP-relaxation analysis across the IEEE
    118-bus number-of-resources experiment.
    """

    results = []

    resource_levels = [
        10,
        15,
        20,
    ]

    availability_prob = 0.45
    suitability_prob = 0.50

    total = (
        len(resource_levels)
        * 100
    )

    counter = 0

    print(
        "\n=== IEEE 118-BUS "
        "LP-RELAXATION ANALYSIS ==="
    )

    for num_resources in resource_levels:
        for seed in range(100):

            counter += 1

            result = (
                run_lp_relaxation_scenario(
                    seed=seed,
                    network="118",
                    num_resources=
                        num_resources,
                    availability_prob=
                        availability_prob,
                    suitability_prob=
                        suitability_prob,
                )
            )

            if result is not None:
                results.append(
                    result
                )

            if counter % 100 == 0:
                print(
                    "IEEE 118 progress: "
                    f"{counter}/{total}"
                )

            gp.disposeDefaultEnv()
            gc.collect()

    return pd.DataFrame(
        results
    )


# =========================================================
# SUMMARY
# =========================================================

def print_summary(
    df,
    network_name,
):
    """
    Print LP-relaxation integrality statistics.
    """

    print(
        f"\n=== {network_name} "
        "LP-RELAXATION SUMMARY ==="
    )

    tested = len(df)

    overlapping = int(
        df[
            "secondary_classes_overlap"
        ].sum()
    )

    quantity_fractional = int(
        (
            ~df[
                "quantity_integral"
            ]
        ).sum()
    )

    quality_fractional = int(
        (
            ~df[
                "quality_integral"
            ]
        ).sum()
    )

    quantity_max_fractionality = (
        df[
            "quantity_maximum_fractionality"
        ].max()
    )

    quality_max_fractionality = (
        df[
            "quality_maximum_fractionality"
        ].max()
    )

    print(
        f"Scenarios tested: {tested}"
    )

    print(
        "Scenarios with overlapping "
        "secondary classes: "
        f"{overlapping}"
    )

    print(
        "Quantity fractional scenarios: "
        f"{quantity_fractional}"
    )

    print(
        "Quality fractional scenarios: "
        f"{quality_fractional}"
    )

    print(
        "Maximum Quantity fractionality: "
        f"{quantity_max_fractionality:.6f}"
    )

    print(
        "Maximum Quality fractionality: "
        f"{quality_max_fractionality:.6f}"
    )

    if tested > 0:
        print(
            "Quantity fractional percentage: "
            f"{100 * quantity_fractional / tested:.2f}%"
        )

        print(
            "Quality fractional percentage: "
            f"{100 * quality_fractional / tested:.2f}%"
        )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # IEEE 33
    # -----------------------------------------------------

    ieee33_df = (
        run_ieee33_lp_analysis()
    )

    ieee33_path = (
        DATA_DIR
        / "ieee33_lp_relaxation_results.csv"
    )

    ieee33_df.to_csv(
        ieee33_path,
        index=False,
    )

    # -----------------------------------------------------
    # IEEE 118
    # -----------------------------------------------------

    ieee118_df = (
        run_ieee118_lp_analysis()
    )

    ieee118_path = (
        DATA_DIR
        / "ieee118_lp_relaxation_results.csv"
    )

    ieee118_df.to_csv(
        ieee118_path,
        index=False,
    )

    print("\nFiles saved:")
    print(f" - {ieee33_path}")
    print(f" - {ieee118_path}")