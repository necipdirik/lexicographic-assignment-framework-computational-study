import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from gurobipy import GRB, Model

from verification.gurobi.verification_gurobi_instance_no_available_assignments import (
    R,
    N,
    C,
    H,
    a,
    s,
    b,
    w,
)


def value(r, n):
    return sum(b[(n, c)] for c in C) + s[(r, n)] + 1


model = Model("verification_instance")

x = model.addVars(R, N, vtype=GRB.BINARY, name="x")
epsilon = model.addVars(C, lb=0, vtype=GRB.CONTINUOUS, name="epsilon")

# =========================================================
# SUB-PROBLEM 1
# =========================================================
model_h = Model("subproblem_1_M_H")

x_h = model_h.addVars(R, H, vtype=GRB.BINARY, name="x")

model_h.setObjective(
    sum(a[(r, n)] * x_h[r, n] for r in R for n in H),
    GRB.MAXIMIZE,
)

for n in H:
    model_h.addConstr(sum(a[(r, n)] * x_h[r, n] for r in R) <= 1)

for r in R:
    model_h.addConstr(sum(a[(r, n)] * x_h[r, n] for n in H) <= 1)

model_h.optimize()

if model_h.Status != GRB.OPTIMAL:
    raise RuntimeError(f"Sub1F status: {model_h.Status}")

M_H = int(round(model_h.ObjVal))

# =========================================================
# SUB-PROBLEM 2
# =========================================================
M_c = {}

for c in C:
    model_c = Model(f"subproblem_2_{c}")

    x_c = model_c.addVars(R, N, vtype=GRB.BINARY, name="x")

    model_c.setObjective(
        sum(b[(n, c)] * a[(r, n)] * x_c[r, n] for r in R for n in N),
        GRB.MAXIMIZE,
    )

    for n in N:
        model_c.addConstr(sum(a[(r, n)] * x_c[r, n] for r in R) <= 1)

    for r in R:
        model_c.addConstr(sum(a[(r, n)] * x_c[r, n] for n in N) <= 1)

    model_c.optimize()

    if model_c.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Sub2F status for {c}: {model_c.Status}")

    M_c[c] = int(round(model_c.ObjVal))

# =========================================================
# MAIN PROBLEM
# =========================================================
model.setObjective(
    sum(value(r, n) * a[(r, n)] * x[r, n] for r in R for n in N)
    - sum(w[c] * epsilon[c] for c in C),
    GRB.MAXIMIZE,
)

for n in N:
    model.addConstr(sum(a[(r, n)] * x[r, n] for r in R) <= 1)

for r in R:
    model.addConstr(sum(a[(r, n)] * x[r, n] for n in N) <= 1)

model.addConstr(
    sum(a[(r, n)] * x[r, n] for r in R for n in H) >= M_H
)

for c in C:
    model.addConstr(
        sum(
            b[(n, c)] * a[(r, n)] * x[r, n]
            for r in R
            for n in N
        )
        + epsilon[c]
        >= M_c[c]
    )

model.optimize()

if model.Status != GRB.OPTIMAL:
    raise RuntimeError(f"MPF status: {model.Status}")

print("\n=== VERIFICATION RESULTS ===")
print(f"M_H = {M_H}")
print(f"M_c = {M_c}")
print(f"Main objective = {model.ObjVal}")

print("\nAssignments:")
for r in R:
    for n in N:
        if a[(r, n)] == 1 and x[r, n].X > 0.5:
            print(f"{r} -> {n}")

print("\nSlack values:")
for c in C:
    print(f"{c}: {epsilon[c].X}")