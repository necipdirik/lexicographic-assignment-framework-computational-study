import random

import gurobipy as gp
from gurobipy import GRB
import pandapower.networks as pn

import time

# =========================================================
# IEEE 33-BUS DATA LOADING
# =========================================================
def load_ieee33_data():
    """
    Load the IEEE 33-bus system and extract demand-node values.
    """
    net = pn.case33bw()

    # Demand nodes are represented by load buses.
    N = sorted(set(int(b) for b in net.load.bus.values))

    return N

# =========================================================
# IEEE 118-BUS DATA LOADING
# =========================================================
def load_ieee118_data():
    """
    Load the IEEE 118-bus system and extract demand-node values.
    """
    net = pn.case118()

    # Demand nodes are represented by load buses.
    N = sorted(set(int(b) for b in net.load.bus.values))

    return N

# =========================================================
# SCENARIO GENERATION
# =========================================================
def generate_scenario(
    N,
    seed=42,
    num_resources=7,
    highest_priority_count=5,
    secondary_class_counts=None,
    availability_prob=0.45,
):
    """
    Generate resources, priority sets and classes, and available 
    resource-to-node pairs.
    """

    if secondary_class_counts is None:
        secondary_class_counts = {
            "class_1": 5,
            "class_2": 5,
            "class_3": 5,
        }

    rng = random.Random(seed)

    R = list(range(num_resources))

    # H: highest-priority demand nodes.
    H = set(rng.sample(N, highest_priority_count))

    # C: index set of secondary-priority classes defined over demand 
    # nodes.
    C = list(secondary_class_counts.keys())

    # Keep H separate from secondary priority classes.
    secondary_candidates = [
        n
        for n in N
        if n not in H
    ]

    class_nodes = {}

    # Secondary priority classes may overlap.
    for c in C:
        class_count = secondary_class_counts[c]

        class_nodes[c] = set(
            rng.sample(
                secondary_candidates,
                class_count,
            )
        )

    # Available resource-to-node pairs.
    available_pairs = []

    for r in R:
        for n in N:
            if rng.random() < availability_prob:
                available_pairs.append((r, n))

    # Ensure that every demand node has at least one available resource.
    for n in N:
        if not any(nn == n for _, nn in available_pairs):
            available_pairs.append((rng.choice(R), n))

    available_pairs = sorted(set(available_pairs))

    return (
        R,
        H,
        C,
        class_nodes,
        available_pairs,
    )

# =========================================================
# SHARED MODEL HELPERS
# =========================================================
def add_assignment_constraints(model, x, available_pairs, R, N):
    """
    Limit each resource and demand node to at most one assignment.
    """

    # Each resource can be assigned to at most one demand node.
    for r in R:
        model.addConstr(
            gp.quicksum(
                x[r, n]
                for rr, n in available_pairs
                if rr == r
            )
            <= 1,
            name=f"resource_{r}",
        )

    # Each demand node can receive at most one resource.
    for n in N:
        model.addConstr(
            gp.quicksum(
                x[r, n]
                for r, nn in available_pairs
                if nn == n
            )
            <= 1,
            name=f"node_{n}",
        )


def collect_solution(
    x,
    available_pairs,
    assignment_value,
    H,
    C,
    class_nodes,
    formulation_name,
    slack_vars=None,
):
    """
    Collect assignment results and performance metrics from 
    a solved formulation.
    """

    selected_pairs = [
        (r, n)
        for r, n in available_pairs
        if x[r, n].X > 0.5
    ]

    total_assignment_value = sum(
        assignment_value[r, n]
        for r, n in selected_pairs
    )

    highest_priority_covered = sum(
        1
        for _, n in selected_pairs
        if n in H
    )

    secondary_priority_covered = {
        c: sum(
            1
            for _, n in selected_pairs
            if n in class_nodes[c]
        )
        for c in C
    }

    slack_values = (
        {
            c: slack_vars[c].X
            for c in C
        }
        if slack_vars is not None
        else {
            c: 0.0
            for c in C
        }
    )

    return {
        "formulation": formulation_name,
        "assignments": len(selected_pairs),
        "assignment_value": total_assignment_value,
        "highest_priority_covered": highest_priority_covered,
        "secondary_priority_covered": secondary_priority_covered,
        "slack": slack_values,
        "selected_pairs": selected_pairs,
    }

# =========================================================
# SUB-PROBLEM 1 FORMULATION
# =========================================================
def solve_subproblem_1(R, available_pairs, H):
    """
    Return M_H: maximum coverage of highest-priority demand 
    nodes.
    """

    model = gp.Model("subproblem_1")
    model.Params.OutputFlag = 0

    highest_priority_pairs = [
        (r, n) for r, n in available_pairs if n in H
    ]

    x = model.addVars(
        highest_priority_pairs,
        vtype=GRB.BINARY,
        name="x",
    )

    add_assignment_constraints(
        model,
        x,
        highest_priority_pairs,
        R,
        H,
    )

    model.setObjective(
        gp.quicksum(x[r, n] for r, n in highest_priority_pairs),
        GRB.MAXIMIZE,
    )

    model.optimize()

    if model.Status != GRB.OPTIMAL:
        model.dispose()
        return None

    M_H = int(round(model.ObjVal))

    model.dispose()

    return M_H

# =========================================================
# SUB-PROBLEM 2 FORMULATION
# =========================================================
def solve_subproblem_2(
    R,
    N,
    available_pairs,
    C,
    class_nodes,
):
    """Return M_c for each secondary priority class c in C."""

    M_c = {}

    for c in C:
        model = gp.Model(f"subproblem_2_{c}")
        model.Params.OutputFlag = 0

        x = model.addVars(
            available_pairs,
            vtype=GRB.BINARY,
            name="x",
        )

        add_assignment_constraints(
            model,
            x,
            available_pairs,
            R,
            N,
        )

        model.setObjective(
            gp.quicksum(
                x[r, n]
                for r, n in available_pairs
                if n in class_nodes[c]
            ),
            GRB.MAXIMIZE,
        )

        model.optimize()

        if model.Status != GRB.OPTIMAL:
            model.dispose()
            return None

        M_c[c] = int(round(model.ObjVal))

        model.dispose()

    return M_c

# =========================================================
# QUANTITY FORMULATION
# =========================================================
def solve_quantity_formulation(
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
):
    """ 
    Maximize assignment count minus penalties for SP target shortfalls 
    while enforcing the HP target M_H.
    """

    model = gp.Model("quantity_formulation")
    model.Params.OutputFlag = 0

    x = model.addVars(
        available_pairs,
        vtype=GRB.BINARY,
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
            name=f"secondary_priority_protection_{c}",
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

    start_time = time.time()
    model.optimize()
    solve_time = time.time() - start_time

    if model.Status != GRB.OPTIMAL:
        model.dispose()
        return None

    result = collect_solution(
        x,
        available_pairs,
        assignment_value,
        H,
        C,
        class_nodes,
        "Quantity",
        epsilon,
    )

    result["solve_time"] = solve_time
    result["M_H"] = M_H
    result["M_c"] = M_c

    model.dispose()

    return result

# =========================================================
# QUALITY FORMULATION
# =========================================================
def solve_quality_formulation(
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
    Maximize assignment value minus penalties for SP target shortfalls
    while fixing the assignment count and enforcing the HP target M_H.
    """

    model = gp.Model("quality_formulation")
    model.Params.OutputFlag = 0

    x = model.addVars(
        available_pairs,
        vtype=GRB.BINARY,
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
            name=f"secondary_priority_protection_{c}",
        )

    model.setObjective(
        gp.quicksum(
            assignment_value[r, n] * x[r, n]
            for r, n in available_pairs
        )
        - gp.quicksum(
            penalty_weights[c] * epsilon[c]
            for c in C
        ),
        GRB.MAXIMIZE,
    )

    start_time = time.time()
    model.optimize()
    solve_time = time.time() - start_time

    if model.Status != GRB.OPTIMAL:
        model.dispose()
        return None

    result = collect_solution(
        x,
        available_pairs,
        assignment_value,
        H,
        C,
        class_nodes,
        "Quality",
        epsilon,
    )

    result["solve_time"] = solve_time
    result["M_H"] = M_H
    result["M_c"] = M_c
    result["maximum_assignments"] = maximum_assignments
    result["objective_value"] = model.ObjVal

    model.dispose()

    return result

# =========================================================
# AGGREGATE-VALUE FORMULATION
# =========================================================
def solve_aggregate_value_formulation(
    R,
    N,
    available_pairs,
    assignment_value,
    H,
    C,
    class_nodes,
):
    """
    Maximize total assignment value without explicit priority 
    protection.
    """

    model = gp.Model("aggregate_value_formulation")
    model.Params.OutputFlag = 0

    x = model.addVars(
        available_pairs,
        vtype=GRB.BINARY,
        name="x",
    )

    add_assignment_constraints(
        model,
        x,
        available_pairs,
        R,
        N,
    )

    model.setObjective(
        gp.quicksum(
            assignment_value[r, n] * x[r, n]
            for r, n in available_pairs
        ),
        GRB.MAXIMIZE,
    )

    start_time = time.time()
    model.optimize()
    solve_time = time.time() - start_time

    if model.Status != GRB.OPTIMAL:
        model.dispose()
        return None

    result = collect_solution(
        x,
        available_pairs,
        assignment_value,
        H,
        C,
        class_nodes,
        "Aggregate-Value",
    )

    result["solve_time"] = solve_time
    result["objective_value"] = model.ObjVal

    model.dispose()

    return result

# =========================================================
# SINGLE SCENARIO RUNNER
# =========================================================
def run_single_scenario(
    seed,
    num_resources=7,
    highest_priority_count=5,
    secondary_class_counts=None,
    availability_prob=0.45,
    suitability_prob=0.50,
    penalty_weight=0.5,
    network="33",
):
    """
    Generate one scenario and solve the Sub-problem 1 Formulation,
    Sub-problem 2 Formulation, Quantity Formulation, Quality
    Formulation, and Aggregate-Value Formulation.
    """

    if network == "33":
        N = load_ieee33_data()
    elif network == "118":
        N = load_ieee118_data()
    else:
        raise ValueError(
            f"Unsupported network type: {network}"
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
        highest_priority_count=highest_priority_count,
        secondary_class_counts=secondary_class_counts,
        availability_prob=availability_prob,
    )

    # Apply the same penalty weight to every secondary priority class.
    penalty_weights = {
        c: penalty_weight
        for c in C
    }

    # Generate binary suitability for every resource-demand node pair
    # using a separate random number generator.
    suitability_rng = random.Random(seed + 1)

    suitability = {
        (r, n): int(
            suitability_rng.random() < suitability_prob
        )
        for r in R
        for n in N
    }

    # Assignment value: v_{r,n} = sum_{c in C} b_{n,c} + s_{r,n} + 1.
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

    M_H = solve_subproblem_1(
        R,
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
        return {
            "seed": seed,
            "network": network,
            "num_resources": num_resources,
            "availability_prob": availability_prob,
            "suitability_prob": suitability_prob,
            "status": "infeasible",
            "quantity": None,
            "quality": None,
            "aggregate_value": None,
        }

    quantity = solve_quantity_formulation(
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

    if quantity is None:
        return {
            "seed": seed,
            "network": network,
            "num_resources": num_resources,
            "availability_prob": availability_prob,
            "suitability_prob": suitability_prob,
            "status": "infeasible",
            "quantity": None,
            "quality": None,
            "aggregate_value": None,
        }

    quality = solve_quality_formulation(
        R,
        N,
        available_pairs,
        assignment_value,
        H,
        C,
        class_nodes,
        M_H,
        M_c,
        quantity["assignments"],
        penalty_weights,
    )

    if quality is None:
        return {
            "seed": seed,
            "network": network,
            "num_resources": num_resources,
            "availability_prob": availability_prob,
            "suitability_prob": suitability_prob,
            "status": "infeasible",
            "quantity": quantity,
            "quality": None,
            "aggregate_value": None,
        }

    aggregate_value = solve_aggregate_value_formulation(
        R,
        N,
        available_pairs,
        assignment_value,
        H,
        C,
        class_nodes,
    )

    if aggregate_value is None:
        return {
            "seed": seed,
            "network": network,
            "num_resources": num_resources,
            "availability_prob": availability_prob,
            "suitability_prob": suitability_prob,
            "status": "infeasible",
            "quantity": quantity,
            "quality": quality,
            "aggregate_value": None,
        }

    return {
        "seed": seed,
        "network": network,
        "num_resources": num_resources,
        "availability_prob": availability_prob,
        "suitability_prob": suitability_prob,
        "status": "optimal",
        "quantity": quantity,
        "quality": quality,
        "aggregate_value": aggregate_value,
    }

# =========================================================
# DEMAND-NODE COUNT CHECK
# =========================================================

if __name__ == "__main__":
    N33 = load_ieee33_data()
    N118 = load_ieee118_data()

    print("IEEE 33 demand nodes:", len(N33))
    print("IEEE 118 demand nodes:", len(N118))