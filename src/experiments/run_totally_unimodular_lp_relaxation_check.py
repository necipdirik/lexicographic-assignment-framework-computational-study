import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.experiments.scenario_solver import (
    load_ieee33_data,
    generate_scenario,
    add_assignment_constraints,
    solve_subproblem_1,
    solve_subproblem_2,
)

import gurobipy as gp
from gurobipy import GRB


TOLERANCE = 1e-6


def is_integer_solution(model_vars) -> tuple[bool, float]:
    """
    Check whether all variable values are integer within tolerance.
    Returns:
        (is_integer, maximum_fractionality)
    """
    max_fractionality = 0.0

    for var in model_vars.values():
        value = var.X
        fractionality = abs(value - round(value))

        max_fractionality = max(max_fractionality, fractionality)

        if fractionality > TOLERANCE:
            return False, max_fractionality

    return True, max_fractionality


def solve_quantity_lp_relaxation(
    R,
    J,
    feasible_pairs,
    critical_nodes,
    F,
):
    m = gp.Model("quantity_lp_relaxation")
    m.Params.OutputFlag = 0

    x = m.addVars(
        feasible_pairs,
        lb=0.0,
        ub=1.0,
        vtype=GRB.CONTINUOUS,
        name="x",
    )

    add_assignment_constraints(m, x, feasible_pairs, R, J)

    m.addConstr(
        gp.quicksum(x[r, j] for (r, j) in feasible_pairs if j in critical_nodes)
        >= F,
        name="critical_protection_F",
    )

    m.setObjective(
        gp.quicksum(x[r, j] for (r, j) in feasible_pairs),
        GRB.MAXIMIZE,
    )

    m.optimize()

    return is_integer_solution(x)


def solve_quality_lp_relaxation(
    R,
    J,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    F,
    T_v,
    assignment_count,
):
    m = gp.Model("quality_lp_relaxation")
    m.Params.OutputFlag = 0

    x = m.addVars(
        feasible_pairs,
        lb=0.0,
        ub=1.0,
        vtype=GRB.CONTINUOUS,
        name="x",
    )

    s = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="s_vulnerable")

    add_assignment_constraints(m, x, feasible_pairs, R, J)

    m.addConstr(
        gp.quicksum(x[r, j] for (r, j) in feasible_pairs)
        == assignment_count,
        name="same_assignment_count",
    )

    m.addConstr(
        gp.quicksum(x[r, j] for (r, j) in feasible_pairs if j in critical_nodes)
        >= F,
        name="critical_protection_F",
    )

    m.addConstr(
        gp.quicksum(x[r, j] for (r, j) in feasible_pairs if j in vulnerable_nodes)
        + s
        >= T_v,
        name="vulnerable_soft_protection",
    )

    m.setObjective(
        gp.quicksum(node_value[j] * x[r, j] for (r, j) in feasible_pairs)
        - 0.50 * s,
        GRB.MAXIMIZE,
    )

    m.optimize()

    return is_integer_solution(x)


def solve_weighted_lp_relaxation(
    R,
    J,
    feasible_pairs,
    node_value,
):
    m = gp.Model("weighted_lp_relaxation")
    m.Params.OutputFlag = 0

    x = m.addVars(
        feasible_pairs,
        lb=0.0,
        ub=1.0,
        vtype=GRB.CONTINUOUS,
        name="x",
    )

    add_assignment_constraints(m, x, feasible_pairs, R, J)

    m.setObjective(
        gp.quicksum(node_value[j] * x[r, j] for (r, j) in feasible_pairs),
        GRB.MAXIMIZE,
    )

    m.optimize()

    return is_integer_solution(x)


def main():
    print("\n=== TUM / LP RELAXATION CHECK ===")

    seed = 100

    _, J, node_value = load_ieee33_data()

    R, critical_nodes, vulnerable_nodes, feasible_pairs = generate_scenario(
        J,
        seed=seed,
        num_resources=7,
        critical_count=5,
        vulnerable_count=5,
        feasibility_prob=0.45,
    )

    F = solve_subproblem_1(R, J, feasible_pairs, critical_nodes)
    T_v = solve_subproblem_2(R, J, feasible_pairs, vulnerable_nodes)

    quantity_integer, quantity_frac = solve_quantity_lp_relaxation(
        R,
        J,
        feasible_pairs,
        critical_nodes,
        F,
    )

    assignment_count = min(len(R), len(J))

    quality_integer, quality_frac = solve_quality_lp_relaxation(
        R,
        J,
        feasible_pairs,
        node_value,
        critical_nodes,
        vulnerable_nodes,
        F,
        T_v,
        assignment_count,
    )

    weighted_integer, weighted_frac = solve_weighted_lp_relaxation(
        R,
        J,
        feasible_pairs,
        node_value,
    )

    print(f"\nScenario seed: {seed}")

    print(f"\nQuantity LP integer solution : {quantity_integer}")
    print(f"Maximum fractionality        : {quantity_frac:.10f}")

    print(f"\nQuality LP integer solution  : {quality_integer}")
    print(f"Maximum fractionality        : {quality_frac:.10f}")

    print(f"\nWeighted LP integer solution : {weighted_integer}")
    print(f"Maximum fractionality        : {weighted_frac:.10f}")


if __name__ == "__main__":
    main()