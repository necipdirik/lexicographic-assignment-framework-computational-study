import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from gurobipy import GRB, Model

from verification.gurobi.verification_gurobi_instance_scarcity import R, N, C, H, D, P, a, w


def value(r, n):
    return sum(a[(n, c)] for c in C) + P[(r, n)] + 1


model = Model("verification_instance")

E = model.addVars(R, N, vtype=GRB.BINARY, name="E")
epsilon = model.addVars(C, lb=0, vtype=GRB.CONTINUOUS, name="epsilon")

# -------------------------
# Subproblem 1: maximize F
# -------------------------
model_f = Model("subproblem_1_F")

E_f = model_f.addVars(R, H, vtype=GRB.BINARY, name="E")

model_f.setObjective(
    sum(D[(r, n)] * E_f[r, n] for r in R for n in H),
    GRB.MAXIMIZE,
)

for n in H:
    model_f.addConstr(sum(D[(r, n)] * E_f[r, n] for r in R) <= 1)

for r in R:
    model_f.addConstr(sum(D[(r, n)] * E_f[r, n] for n in H) <= 1)

model_f.optimize()

F = int(round(model_f.ObjVal))

# -------------------------
# Subproblem 2: maximize Tc
# -------------------------
T = {}

for c in C:
    model_t = Model(f"subproblem_2_{c}")

    E_t = model_t.addVars(R, N, vtype=GRB.BINARY, name="E")

    model_t.setObjective(
        sum(a[(n, c)] * D[(r, n)] * E_t[r, n] for r in R for n in N),
        GRB.MAXIMIZE,
    )

    for n in N:
        model_t.addConstr(sum(D[(r, n)] * E_t[r, n] for r in R) <= 1)

    for r in R:
        model_t.addConstr(sum(D[(r, n)] * E_t[r, n] for n in N) <= 1)

    model_t.optimize()

    T[c] = int(round(model_t.ObjVal))

# -------------------------
# Main problem
# -------------------------
model.setObjective(
    sum(value(r, n) * D[(r, n)] * E[r, n] for r in R for n in N)
    - sum(w[c] * epsilon[c] for c in C),
    GRB.MAXIMIZE,
)

for n in N:
    model.addConstr(sum(D[(r, n)] * E[r, n] for r in R) <= 1)

for r in R:
    model.addConstr(sum(D[(r, n)] * E[r, n] for n in N) <= 1)

model.addConstr(
    sum(D[(r, n)] * E[r, n] for r in R for n in H) >= F
)

for c in C:
    model.addConstr(
        sum(a[(n, c)] * D[(r, n)] * E[r, n] for r in R for n in N) + epsilon[c] >= T[c]
    )

model.optimize()

print("\n=== VERIFICATION RESULTS ===")
print(f"F = {F}")
print(f"T = {T}")
print(f"Main objective = {model.ObjVal}")

print("\nAssignments:")
for r in R:
    for n in N:
        if E[r, n].X > 0.5:
            print(f"{r} -> {n}")

print("\nSlack values:")
for c in C:
    print(f"{c}: {epsilon[c].X}")