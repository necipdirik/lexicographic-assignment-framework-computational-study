import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandapower.networks as pn

net = pn.case57()

print("=== BASIC INFO ===")
print("Number of buses:", len(net.bus))
print("Number of loads:", len(net.load))
print("Number of lines:", len(net.line))
print("Number of generators:", len(net.gen))
print("Number of external grids:", len(net.ext_grid))

print("\n=== BUS TABLE ===")
print(net.bus.head(10))

print("\n=== LOAD TABLE ===")
print(net.load.head(10))

print("\n=== LINE TABLE ===")
print(net.line.head(10))





from src.experiments.scenario_solver import load_ieee57_data, generate_scenario

_, J, node_value = load_ieee57_data()

R, critical_nodes, vulnerable_nodes, feasible_pairs = generate_scenario(
    J,
    seed=0,
    num_resources=12,
    feasibility_prob=0.45,
)

print("\n=== SCENARIO SIZE ===")
print("J (nodes):", len(J))
print("R (resources):", len(R))
print("F (feasible pairs):", len(feasible_pairs))