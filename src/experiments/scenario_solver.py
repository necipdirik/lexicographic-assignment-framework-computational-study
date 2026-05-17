import random

import gurobipy as gp
from gurobipy import GRB
import pandapower.networks as pn

import time


# =========================================================
# IEEE 33-BUS DATA LOADING
# =========================================================
def load_ieee33_data():
    """Load the IEEE 33-bus system and extract demand-node values."""
    net = pn.case33bw()

    # Demand nodes are represented by load buses.
    J = sorted(set(int(b) for b in net.load.bus.values))

    # Node values are based on real active load demand.
    node_value = {}
    for j in J:
        demand = float(net.load.loc[net.load.bus == j, "p_mw"].sum())
        node_value[j] = demand

    return net, J, node_value


# =========================================================
# IEEE 57-BUS DATA LOADING
# =========================================================

def load_ieee57_data():
    """Load the IEEE 57-bus system and extract demand-node values."""
    net = pn.case57()

    # Demand nodes are represented by load buses.
    J = sorted(set(int(b) for b in net.load.bus.values))

    # Node values are based on real active load demand.
    node_value = {}
    for j in J:
        demand = float(net.load.loc[net.load.bus == j, "p_mw"].sum())
        node_value[j] = demand

    return net, J, node_value


# =========================================================
# IEEE 118-BUS DATA LOADING
# =========================================================
def load_ieee118_data():
    """Load the IEEE 118-bus system and extract demand-node values."""
    net = pn.case118()

    J = sorted(set(int(b) for b in net.load.bus.values))

    node_value = {}
    for j in J:
        demand = float(net.load.loc[net.load.bus == j, "p_mw"].sum())
        node_value[j] = demand

    return net, J, node_value

# =========================================================
# SCENARIO GENERATION
# =========================================================
def generate_scenario(
    J,
    seed=42,
    num_resources=7,
    critical_count=5,
    vulnerable_count=5,
    feasibility_prob=0.45,
):
    """Generate resources, priority node groups, and feasible assignment pairs."""
    random.seed(seed)

    R = list(range(num_resources))

    critical_nodes = set(random.sample(J, critical_count))

    remaining_nodes = [j for j in J if j not in critical_nodes]
    vulnerable_nodes = set(random.sample(remaining_nodes, vulnerable_count))

    feasible_pairs = []

    for r in R:
        for j in J:
            if random.random() < feasibility_prob:
                feasible_pairs.append((r, j))

    # Ensure every demand node has at least one feasible resource.
    for j in J:
        if not any(j == jj for _, jj in feasible_pairs):
            feasible_pairs.append((random.choice(R), j))

    feasible_pairs = sorted(set(feasible_pairs))

    return R, critical_nodes, vulnerable_nodes, feasible_pairs


# =========================================================
# SHARED MODEL HELPERS
# =========================================================
def add_assignment_constraints(model, x, feasible_pairs, R, J):
    """Add one-to-one assignment constraints for resources and demand nodes."""
    for r in R:
        model.addConstr(
            gp.quicksum(x[r, j] for rr, j in feasible_pairs if rr == r) <= 1,
            name=f"resource_{r}",
        )

    for j in J:
        model.addConstr(
            gp.quicksum(x[r, j] for r, jj in feasible_pairs if jj == j) <= 1,
            name=f"node_{j}",
        )


def collect_solution(
    x,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    model_name,
    slack_var=None,
):
    """Collect assignment results and performance metrics from a solved model."""
    selected = [(r, j) for (r, j) in feasible_pairs if x[r, j].X > 0.5]

    total_value = sum(node_value[j] for (_, j) in selected)
    critical_covered = sum(1 for (_, j) in selected if j in critical_nodes)
    vulnerable_covered = sum(1 for (_, j) in selected if j in vulnerable_nodes)
    slack_value = slack_var.X if slack_var is not None else 0.0

    return {
        "model": model_name,
        "assignments": len(selected),
        "value": total_value,
        "critical_covered": critical_covered,
        "vulnerable_covered": vulnerable_covered,
        "slack": slack_value,
        "selected_pairs": selected,
    }

def solve_subproblem_1(R, J, feasible_pairs, critical_nodes):
    """Solve Sub-problem 1 and return F: maximum critical-node coverage."""
    m = gp.Model("subproblem_1")
    m.Params.OutputFlag = 0

    x = m.addVars(feasible_pairs, vtype=GRB.BINARY, name="x")

    add_assignment_constraints(m, x, feasible_pairs, R, J)

    m.setObjective(
        gp.quicksum(x[r, j] for (r, j) in feasible_pairs if j in critical_nodes),
        GRB.MAXIMIZE,
    )

    m.optimize()

    if m.Status != GRB.OPTIMAL:
        return None

    return int(round(m.ObjVal))


def solve_subproblem_2(R, J, feasible_pairs, vulnerable_nodes):
    """Solve Sub-problem 2 and return T_v: maximum vulnerable-node coverage."""
    m = gp.Model("subproblem_2")
    m.Params.OutputFlag = 0

    x = m.addVars(feasible_pairs, vtype=GRB.BINARY, name="x")

    add_assignment_constraints(m, x, feasible_pairs, R, J)

    m.setObjective(
        gp.quicksum(x[r, j] for (r, j) in feasible_pairs if j in vulnerable_nodes),
        GRB.MAXIMIZE,
    )

    m.optimize()

    if m.Status != GRB.OPTIMAL:
        return None

    return int(round(m.ObjVal))


# =========================================================
# QUANTITY MODEL
# =========================================================
import time

def solve_quantity_model(
    R,
    J,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    F,
    T_v,
):
    """Solve the Quantity model, preserving F and maximizing total assignments."""
    m_qty = gp.Model("quantity_model")
    m_qty.Params.OutputFlag = 0

    x_qty = m_qty.addVars(feasible_pairs, vtype=GRB.BINARY, name="x")

    add_assignment_constraints(m_qty, x_qty, feasible_pairs, R, J)

    m_qty.addConstr(
        gp.quicksum(x_qty[r, j] for (r, j) in feasible_pairs if j in critical_nodes)
        >= F,
        name="critical_protection_F",
    )

    m_qty.setObjective(
        gp.quicksum(x_qty[r, j] for (r, j) in feasible_pairs),
        GRB.MAXIMIZE,
    )

    start = time.time()
    m_qty.optimize()
    end = time.time()
    solve_time = end - start

    if m_qty.Status != GRB.OPTIMAL:
        return None

    result = collect_solution(
        x_qty,
        feasible_pairs,
        node_value,
        critical_nodes,
        vulnerable_nodes,
        "Quantity",
    )

    result["solve_time"] = solve_time
    result["F"] = F
    result["T_v"] = T_v

    return result


# =========================================================
# QUALITY MODEL
# =========================================================
def solve_quality_model(
    R,
    J,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    F,
    T_v,
    quantity_assignments,
    penalty_weight=0.50,
):
    """Solve the Quality model using F, T_v, and the assignment count M."""
    m_qual = gp.Model("quality_model")
    m_qual.Params.OutputFlag = 0

    x_qual = m_qual.addVars(feasible_pairs, vtype=GRB.BINARY, name="x")
    s_qual = m_qual.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="s_vulnerable")

    add_assignment_constraints(m_qual, x_qual, feasible_pairs, R, J)

    m_qual.addConstr(
        gp.quicksum(x_qual[r, j] for (r, j) in feasible_pairs) == quantity_assignments,
        name="same_assignment_count_M",
    )

    m_qual.addConstr(
        gp.quicksum(x_qual[r, j] for (r, j) in feasible_pairs if j in critical_nodes)
        >= F,
        name="critical_protection_F",
    )

    m_qual.addConstr(
        gp.quicksum(x_qual[r, j] for (r, j) in feasible_pairs if j in vulnerable_nodes)
        + s_qual
        >= T_v,
        name="vulnerable_soft_protection_Tv",
    )

    m_qual.setObjective(
        gp.quicksum(node_value[j] * x_qual[r, j] for (r, j) in feasible_pairs)
        - penalty_weight * s_qual,
        GRB.MAXIMIZE,
    )

    start = time.time()
    m_qual.optimize()
    end = time.time()
    solve_time = end - start

    if m_qual.Status != GRB.OPTIMAL:
        return None

    result = collect_solution(
        x_qual,
        feasible_pairs,
        node_value,
        critical_nodes,
        vulnerable_nodes,
        "Quality",
        s_qual,
    )

    result["solve_time"] = solve_time
    result["F"] = F
    result["T_v"] = T_v

    return result

# =========================================================
# PURE WEIGHTED MODEL
# =========================================================
def solve_pure_weighted_model(
    R,
    J,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
):
    """Solve the Pure Weighted model without explicit priority protection."""
    m_w = gp.Model("pure_weighted_model")
    m_w.Params.OutputFlag = 0

    x_w = m_w.addVars(feasible_pairs, vtype=GRB.BINARY, name="x")

    add_assignment_constraints(m_w, x_w, feasible_pairs, R, J)

    m_w.setObjective(
        gp.quicksum(node_value[j] * x_w[r, j] for (r, j) in feasible_pairs),
        GRB.MAXIMIZE,
    )

    start = time.time()
    m_w.optimize()
    end = time.time()
    solve_time = end - start

    if m_w.Status != GRB.OPTIMAL:
        return None

    result = collect_solution(
    x_w,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    "Pure Weighted",
)

    result["solve_time"] = solve_time

    return result


# =========================================================
# SINGLE SCENARIO RUNNER
# =========================================================
def run_single_scenario(
    seed,
    num_resources=7,
    critical_count=5,
    vulnerable_count=5,
    feasibility_prob=0.45,
    network="33",
):
    """Run Quantity, Quality, and Pure Weighted models for one generated scenario."""
    if network == "33":
        _, J, node_value = load_ieee33_data()
    elif network == "57":
        _, J, node_value = load_ieee57_data()
    elif network == "118":
        _, J, node_value = load_ieee118_data()
    else:
        raise ValueError(f"Unsupported network type: {network}")

    R, critical_nodes, vulnerable_nodes, feasible_pairs = generate_scenario(
        J,
        seed=seed,
        num_resources=num_resources,
        critical_count=critical_count,
        vulnerable_count=vulnerable_count,
        feasibility_prob=feasibility_prob,
    )

    F = solve_subproblem_1(R, J, feasible_pairs, critical_nodes)
    T_v = solve_subproblem_2(R, J, feasible_pairs, vulnerable_nodes)

    if F is None or T_v is None:
        return {
            "seed": seed,
            "status": "infeasible",
            "quantity": None,
            "quality": None,
            "weighted": None,
        }

    qty = solve_quantity_model(
        R,
        J,
        feasible_pairs,
        node_value,
        critical_nodes,
        vulnerable_nodes,
        F,
        T_v,
    )

    if qty is None:
        return {
            "seed": seed,
            "status": "infeasible",
            "quantity": None,
            "quality": None,
            "weighted": None,
        }

    qual = solve_quality_model(
        R,
        J,
        feasible_pairs,
        node_value,
        critical_nodes,
        vulnerable_nodes,
        F,
        T_v,
        qty["assignments"],
    )

    if qual is None:
        return {
            "seed": seed,
            "status": "infeasible",
            "quantity": qty,
            "quality": None,
            "weighted": None,
        }

    weighted = solve_pure_weighted_model(
        R,
        J,
        feasible_pairs,
        node_value,
        critical_nodes,
        vulnerable_nodes,
    )

    return {
        "seed": seed,
        "status": "optimal",
        "quantity": qty,
        "quality": qual,
        "weighted": weighted,
    }
