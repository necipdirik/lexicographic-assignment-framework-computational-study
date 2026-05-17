import random

import gurobipy as gp
from gurobipy import GRB
import pandapower.networks as pn


# =========================================================
# 1. LOAD IEEE 33-BUS DATASET
# =========================================================
net = pn.case33bw()

# Demand nodes are represented by load buses.
J = sorted(set(int(b) for b in net.load.bus.values))

# Mobile energy resources.
R = list(range(7))  # 7 resources


# =========================================================
# 2. DEFINE PRIORITY NODE GROUPS
# =========================================================
# Critical nodes represent high-priority loads.
critical_nodes = {3, 6, 10, 15, 20}.intersection(set(J))

# Vulnerable nodes represent secondary priority loads.
vulnerable_nodes = {1, 5, 8, 11, 19}.intersection(set(J))


# =========================================================
# 3. BUILD NODE VALUES FROM LOAD DEMAND
# =========================================================
node_value = {}

for j in J:
    demand = float(net.load.loc[net.load.bus == j, "p_mw"].sum())
    node_value[j] = demand


# =========================================================
# 4. GENERATE FEASIBLE RESOURCE-NODE PAIRS
# =========================================================
random.seed(42)
feasible_pairs = []

for r in R:
    for j in J:
        if random.random() < 0.45:
            feasible_pairs.append((r, j))

# Ensure every demand node has at least one feasible resource.
for j in J:
    if not any(j == jj for _, jj in feasible_pairs):
        feasible_pairs.append((random.choice(R), j))

feasible_pairs = sorted(set(feasible_pairs))


# =========================================================
# 5. DEFINE TARGET LEVELS
# =========================================================
# Critical target is enforced as a hard constraint.
required_critical = min(4, len(critical_nodes))

# Vulnerable target is enforced as a soft constraint with slack.
required_vulnerable = min(2, len(vulnerable_nodes))

# Penalty weight for unmet vulnerable target.
penalty_weight = 0.50


# =========================================================
# 6. HELPER FUNCTIONS
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


def analyze_solution(
    model,
    x,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    model_name,
    slack_var=None,
):
    """Extract and print solution metrics from an optimized model."""

    if model.Status != GRB.OPTIMAL:
        raise RuntimeError(
            f"{model_name} did not solve to optimality. "
            f"Gurobi status code: {model.Status}"
        )

    selected = [(r, j) for (r, j) in feasible_pairs if x[r, j].X > 0.5]
    total_value = sum(node_value[j] for (_, j) in selected)
    critical_covered = sum(1 for (_, j) in selected if j in critical_nodes)
    vulnerable_covered = sum(1 for (_, j) in selected if j in vulnerable_nodes)
    slack_value = slack_var.X if slack_var is not None else 0.0

    print(f"\n=== {model_name} ===")
    print("Assignments:", len(selected))
    print("Total value:", round(total_value, 4))
    print("Critical nodes covered:", critical_covered)
    print("Vulnerable nodes covered:", vulnerable_covered)

    if slack_var is not None:
        print("Slack:", round(slack_value, 4))

    print("Selected pairs:", selected)

    return selected, len(selected), total_value, critical_covered, vulnerable_covered, slack_value


# =========================================================
# 7. MODEL 1 — QUANTITY
# =========================================================
# Objective: maximize the number of assignments.
# Critical nodes are protected through a hard constraint.
# Vulnerable nodes are protected through a soft constraint.
# =========================================================
m_qty = gp.Model("quantity_model")
m_qty.Params.OutputFlag = 0

x_qty = m_qty.addVars(feasible_pairs, vtype=GRB.BINARY, name="x")
s_qty = m_qty.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="s_vulnerable")

add_assignment_constraints(m_qty, x_qty, feasible_pairs, R, J)

m_qty.addConstr(
    gp.quicksum(x_qty[r, j] for (r, j) in feasible_pairs if j in critical_nodes)
    >= required_critical,
    name="critical_protection",
)

m_qty.addConstr(
    gp.quicksum(x_qty[r, j] for (r, j) in feasible_pairs if j in vulnerable_nodes)
    + s_qty
    >= required_vulnerable,
    name="vulnerable_soft_protection",
)

m_qty.setObjective(
    gp.quicksum(x_qty[r, j] for (r, j) in feasible_pairs),
    GRB.MAXIMIZE,
)

m_qty.optimize()

qty_selected, qty_assignments, qty_value, qty_critical, qty_vulnerable, qty_slack = analyze_solution(
    m_qty,
    x_qty,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    "QUANTITY MODEL",
    s_qty,
)


# =========================================================
# 8. MODEL 2 — QUALITY
# =========================================================
# Objective: maximize assignment value while preserving quantity.
# Critical nodes are protected through a hard constraint.
# Vulnerable nodes are protected through a soft constraint.
# =========================================================
m_qual = gp.Model("quality_model")
m_qual.Params.OutputFlag = 0

x_qual = m_qual.addVars(feasible_pairs, vtype=GRB.BINARY, name="x")
s_qual = m_qual.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="s_vulnerable")

add_assignment_constraints(m_qual, x_qual, feasible_pairs, R, J)

m_qual.addConstr(
    gp.quicksum(x_qual[r, j] for (r, j) in feasible_pairs if j in critical_nodes)
    >= required_critical,
    name="critical_protection",
)

m_qual.addConstr(
    gp.quicksum(x_qual[r, j] for (r, j) in feasible_pairs if j in vulnerable_nodes)
    + s_qual
    >= required_vulnerable,
    name="vulnerable_soft_protection",
)

m_qual.addConstr(
    gp.quicksum(x_qual[r, j] for (r, j) in feasible_pairs) == qty_assignments,
    name="same_assignment_count",
)

m_qual.setObjective(
    gp.quicksum(node_value[j] * x_qual[r, j] for (r, j) in feasible_pairs)
    - penalty_weight * s_qual,
    GRB.MAXIMIZE,
)

m_qual.optimize()

qual_selected, qual_assignments, qual_value, qual_critical, qual_vulnerable, qual_slack = analyze_solution(
    m_qual,
    x_qual,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    "QUALITY MODEL",
    s_qual,
)


# =========================================================
# 9. MODEL 3 — PURE WEIGHTED
# =========================================================
# Objective: maximize total assignment value.
# No explicit critical or vulnerable protection is enforced.
# =========================================================
m_w = gp.Model("pure_weighted_model")
m_w.Params.OutputFlag = 0

x_w = m_w.addVars(feasible_pairs, vtype=GRB.BINARY, name="x")

add_assignment_constraints(m_w, x_w, feasible_pairs, R, J)

m_w.setObjective(
    gp.quicksum(node_value[j] * x_w[r, j] for (r, j) in feasible_pairs),
    GRB.MAXIMIZE,
)

m_w.optimize()

w_selected, w_assignments, w_value, w_critical, w_vulnerable, _ = analyze_solution(
    m_w,
    x_w,
    feasible_pairs,
    node_value,
    critical_nodes,
    vulnerable_nodes,
    "PURE WEIGHTED MODEL",
)


# =========================================================
# 10. FINAL SUMMARY
# =========================================================
print("\n================ FINAL SUMMARY ================")
print("Critical nodes:", sorted(critical_nodes))
print("Vulnerable nodes:", sorted(vulnerable_nodes))
print(f"Critical target: {required_critical}")
print(f"Vulnerable target: {required_vulnerable}")
print(f"Penalty weight: {penalty_weight}")
print()

print(
    f"Quantity      -> assignments: {qty_assignments}, value: {round(qty_value, 4)}, "
    f"critical: {qty_critical}, vulnerable: {qty_vulnerable}, slack: {round(qty_slack, 4)}"
)

print(
    f"Quality       -> assignments: {qual_assignments}, value: {round(qual_value, 4)}, "
    f"critical: {qual_critical}, vulnerable: {qual_vulnerable}, slack: {round(qual_slack, 4)}"
)

print(
    f"Pure Weighted -> assignments: {w_assignments}, value: {round(w_value, 4)}, "
    f"critical: {w_critical}, vulnerable: {w_vulnerable}"
)

print("\n--- Quantity vs Quality ---")
print(f"Same assignment count? {'Yes' if qty_assignments == qual_assignments else 'No'}")
print(f"Critical coverage difference: {qual_critical - qty_critical}")
print(f"Vulnerable coverage difference: {qual_vulnerable - qty_vulnerable}")
print(f"Slack difference: {round(qual_slack - qty_slack, 4)}")
print(f"Value improvement: {round(qual_value - qty_value, 4)}")

print("\n--- Quality vs Pure Weighted ---")
print(f"Assignment difference: {w_assignments - qual_assignments}")
print(f"Value difference: {round(w_value - qual_value, 4)}")
print(f"Critical coverage difference: {w_critical - qual_critical}")
print(f"Vulnerable coverage difference: {w_vulnerable - qual_vulnerable}")