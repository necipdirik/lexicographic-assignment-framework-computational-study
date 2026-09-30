import argparse
import hashlib
import importlib.util
import math
import random
from itertools import product
from pathlib import Path

# =========================================================
# SHARED VERIFICATION HELPERS
# =========================================================


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def close(actual, expected, label):
    require(
        math.isclose(
            actual,
            expected,
            rel_tol=1e-8,
            abs_tol=1e-6,
        ),
        f"{label}: expected {expected}, got {actual}",
    )


# =========================================================
# INDEPENDENT EXHAUSTIVE ENUMERATION
# =========================================================


def enumerate_assignments(case):
    """
    Enumerate all feasible assignments, including the empty assignment.
    """

    choices = [
        [None] + [n for rr, n in case["pairs"] if rr == r]
        for r in case["R"]
    ]

    assignments = []

    for selected in product(*choices):
        nodes = [n for n in selected if n is not None]

        if len(nodes) == len(set(nodes)):
            assignments.append(
                tuple(
                    (r, n)
                    for r, n in zip(
                        case["R"],
                        selected,
                    )
                    if n is not None
                )
            )

    return assignments


def coverage(selected, nodes):
    return sum(n in nodes for _, n in selected)


def penalty(case, selected, targets):
    return sum(
        case["weights"][c]
        * max(
            0,
            targets[c]
            - coverage(
                selected,
                case["classes"][c],
            ),
        )
        for c in case["C"]
    )


# =========================================================
# SOLUTION AND METRIC CHECKS
# =========================================================


def verify_result(
    case,
    result,
    formulation,
    targets,
    hp_target,
    expected_objective,
    fixed_count=None,
):
    require(
        result is not None,
        f"{formulation}: no optimal result",
    )

    selected = result["selected_pairs"]

    require(
        len(selected) == len(set(selected)),
        "Duplicate pairs",
    )

    require(
        set(selected) <= set(case["pairs"]),
        "Unavailable pair selected",
    )

    require(
        len({r for r, _ in selected}) == len(selected),
        "Resource assigned more than once",
    )

    require(
        len({n for _, n in selected}) == len(selected),
        "Node assigned more than once",
    )

    count = len(selected)

    value = sum(case["values"][pair] for pair in selected)

    hp = coverage(
        selected,
        case["H"],
    )

    close(
        result["assignments"],
        count,
        "Reported count",
    )

    close(
        result["assignment_value"],
        value,
        "Reported assignment value",
    )

    close(
        result["highest_priority_covered"],
        hp,
        "Reported HP coverage",
    )

    for c in case["C"]:
        covered = coverage(
            selected,
            case["classes"][c],
        )

        close(
            result["secondary_priority_covered"][c],
            covered,
            f"Reported SP coverage for {c}",
        )

        if formulation != "aggregate_value":
            slack = result["slack"][c]

            require(
                slack >= -1e-6,
                f"Negative slack for {c}",
            )

            require(
                covered + slack >= targets[c] - 1e-6,
                f"SP target violated for {c}",
            )

            close(
                slack,
                max(
                    0,
                    targets[c] - covered,
                ),
                f"Slack for {c}",
            )

    if formulation != "aggregate_value":
        require(
            hp >= hp_target,
            "HP target violated",
        )

        require(
            result["M_H"] == hp_target,
            "Reported M_H mismatch",
        )

        require(
            result["M_c"] == targets,
            "Reported M_c mismatch",
        )

        cost = sum(
            case["weights"][c] * result["slack"][c] for c in case["C"]
        )

        objective = (
            count if formulation == "quantity" else value
        ) - cost
    else:
        objective = value

    if fixed_count is not None:
        require(
            count == fixed_count,
            "Quality assignment count changed",
        )

        require(
            result["maximum_assignments"] == fixed_count,
            "Reported fixed count mismatch",
        )

    close(
        objective,
        expected_objective,
        f"{formulation} optimum",
    )

    if "objective_value" in result:
        close(
            result["objective_value"],
            objective,
            "Reported objective",
        )


# =========================================================
# EXPERIMENT FORMULATION CHECKS
# =========================================================


def verify_case(solver, case, pipeline_result=None):
    """
    Call production functions; derive reference optima independently.
    """

    require(
        all(w > 0 for w in case["weights"].values()),
        "Enumeration assumes positive penalty weights",
    )

    matchings = enumerate_assignments(case)

    hp_target = max(
        coverage(
            p,
            case["H"],
        )
        for p in matchings
    )

    targets = {
        c: max(
            coverage(
                p,
                case["classes"][c],
            )
            for p in matchings
        )
        for c in case["C"]
    }

    if "expected_targets" in case:
        require(
            (hp_target, targets) == case["expected_targets"],
            "Hand-calculated targets do not match enumeration",
        )

    actual_hp = solver.solve_subproblem_1(
        case["R"],
        case["pairs"],
        case["H"],
    )

    actual_targets = solver.solve_subproblem_2(
        case["R"],
        case["N"],
        case["pairs"],
        case["C"],
        case["classes"],
    )

    require(
        actual_hp == hp_target,
        f"M_H: {actual_hp} != {hp_target}",
    )

    require(
        actual_targets == targets,
        f"M_c: {actual_targets} != {targets}",
    )

    protected = [
        p
        for p in matchings
        if coverage(
            p,
            case["H"],
        )
        >= hp_target
    ]

    quantity_optimum = max(
        len(p)
        - penalty(
            case,
            p,
            targets,
        )
        for p in protected
    )

    arguments = (
        case["R"],
        case["N"],
        case["pairs"],
        case["values"],
        case["H"],
        case["C"],
        case["classes"],
        actual_hp,
        actual_targets,
    )

    if pipeline_result is None:
        quantity = solver.solve_quantity_formulation(
            *arguments,
            case["weights"],
        )
    else:
        require(
            pipeline_result["status"] == "optimal",
            "Runner status",
        )

        quantity = pipeline_result["quantity"]

    verify_result(
        case,
        quantity,
        "quantity",
        targets,
        hp_target,
        quantity_optimum,
    )
    # Quality fixes the count returned by Quantity. Tied Quantity
    # solutions may have different counts; no tie-break is imposed.

    fixed_count = quantity["assignments"]

    quality_optimum = max(
        sum(case["values"][pair] for pair in p)
        - penalty(
            case,
            p,
            targets,
        )
        for p in protected
        if len(p) == fixed_count
    )

    aggregate_optimum = max(
        sum(case["values"][pair] for pair in p) for p in matchings
    )

    if pipeline_result is None:
        quality = solver.solve_quality_formulation(
            *arguments,
            fixed_count,
            case["weights"],
        )

        aggregate = solver.solve_aggregate_value_formulation(
            *arguments[:7]
        )
    else:
        quality = pipeline_result["quality"]

        aggregate = pipeline_result["aggregate_value"]

    verify_result(
        case,
        quality,
        "quality",
        targets,
        hp_target,
        quality_optimum,
        fixed_count,
    )

    verify_result(
        case,
        aggregate,
        "aggregate_value",
        targets,
        hp_target,
        aggregate_optimum,
    )

    print(
        f"PASS {case['name']}: M_H={hp_target}, M_c={targets}, "
        f"objectives=({quantity_optimum:g}, {quality_optimum:g}, "
        f"{aggregate_optimum:g})"
    )


# =========================================================
# VERIFICATION INSTANCE CONSTRUCTION
# =========================================================


def make_case(name, R, N, pairs, H, classes, suitability, weights):
    return {
        "name": name,
        "R": R,
        "N": N,
        "pairs": pairs,
        "H": set(H),
        "C": list(classes),
        "classes": classes,
        "weights": weights,
        "values": {
            (r, n): 1
            + suitability.get(
                (r, n),
                0,
            )
            + sum(n in nodes for nodes in classes.values())
            for r, n in pairs
        },
    }


# =========================================================
# FIXED VERIFICATION INSTANCES
# =========================================================


def fixed_cases():
    # Same input data as the three existing Gurobi verification 
    # fixtures.

    N = ["n1", "n2", "n3"]

    R = ["r1", "r2", "r3"]

    pairs = [
        ("r1", "n1"),
        ("r1", "n2"),
        ("r2", "n1"),
        ("r2", "n3"),
        ("r3", "n2"),
        ("r3", "n3"),
    ]

    classes = {
        "critical": {"n1"},
        "vulnerable": {"n2", "n3"},
    }

    suitability = {
        ("r1", "n1"): 1,
        ("r2", "n3"): 1,
        ("r3", "n2"): 1,
    }

    weights = {
        "critical": 2,
        "vulnerable": 1,
    }

    for name, resources, edges, targets in [
        (
            "original_normal",
            R,
            pairs,
            (
                1,
                {
                    "critical": 1,
                    "vulnerable": 2,
                },
            ),
        ),
        (
            "original_scarcity",
            R[:2],
            pairs[:4],
            (
                1,
                {
                    "critical": 1,
                    "vulnerable": 2,
                },
            ),
        ),
        (
            "original_no_available_pairs",
            R,
            [],
            (
                0,
                {
                    "critical": 0,
                    "vulnerable": 0,
                },
            ),
        ),
    ]:
        case = make_case(
            name,
            resources,
            N,
            edges,
            ["n1"],
            classes,
            suitability,
            weights,
        )

        case["expected_targets"] = targets

        yield case

    yield make_case(
        "hp_protection",
        [0],
        [0, 1],
        [
            (0, 0),
            (0, 1),
        ],
        [0],
        {
            "a": {1},
            "b": {1},
            "c": {1},
        },
        {},
        {
            "a": 0.5,
            "b": 0.5,
            "c": 0.5,
        },
    )

    yield make_case(
        "overlapping_secondary_classes",
        [0, 1],
        [0, 1, 2, 3],
        [(r, n) for r in [0, 1] for n in [0, 1, 2, 3]],
        [0],
        {
            "a": {1, 2},
            "b": {2, 3},
        },
        {(1, 3): 1},
        {
            "a": 0.25,
            "b": 2,
        },
    )

    yield make_case(
        "unreachable_hp_and_isolated_resource",
        [0, 1],
        [0, 1, 2],
        [
            (0, 1),
            (0, 2),
        ],
        [0],
        {
            "a": {1},
            "b": {2},
        },
        {},
        {
            "a": 1,
            "b": 0.5,
        },
    )

    yield make_case(
        "empty_priority_sets",
        [0, 1],
        [0, 1],
        [
            (0, 0),
            (1, 1),
        ],
        [],
        {},
        {(1, 1): 1},
        {},
    )


# =========================================================
# RANDOM SMALL VERIFICATION INSTANCES
# =========================================================


def random_cases():
    # Independent small graphs; unlike the scenario generator, these 
    # may contain unreachable nodes. H remains separate from secondary 
    # classes.

    for seed in range(24):
        rng = random.Random(seed)

        R, N = list(range(3)), list(range(5))

        pairs = [(r, n) for r in R for n in N if rng.random() < 0.5]

        classes = {
            c: {n for n in N[1:] if rng.random() < 0.5}
            for c in ["a", "b"]
        }

        suitability = {pair: rng.randrange(2) for pair in pairs}

        weights = {c: rng.choice([0.25, 0.5, 1, 2]) for c in classes}

        yield make_case(
            f"random_seed_{seed}",
            R,
            N,
            pairs,
            [0],
            classes,
            suitability,
            weights,
        )


# =========================================================
# SINGLE SCENARIO RUNNER CHECKS
# =========================================================


def verify_runner(solver, network, seed):
    # Use real IEEE demand nodes with just two resources so enumeration
    # stays small. Check runner wiring, suitability, values and metrics.

    loader = (
        solver.load_ieee33_data
        if network == "33"
        else solver.load_ieee118_data
    )

    N = loader()

    class_counts = {
        "a": 2,
        "b": 2,
    }

    R, H, C, classes, pairs = solver.generate_scenario(
        N,
        seed=seed,
        num_resources=2,
        highest_priority_count=2,
        secondary_class_counts=class_counts,
        availability_prob=0.3,
    )

    rng = random.Random(seed + 1)

    suitability = {
        (r, n): int(rng.random() < 0.6) for r in R for n in N
    }

    case = make_case(
        f"runner_ieee{network}_seed_{seed}",
        R,
        N,
        pairs,
        H,
        classes,
        suitability,
        {c: 0.5 for c in C},
    )

    result = solver.run_single_scenario(
        seed,
        num_resources=2,
        highest_priority_count=2,
        secondary_class_counts=class_counts,
        availability_prob=0.3,
        suitability_prob=0.6,
        penalty_weight=0.5,
        network=network,
    )

    require(
        result["seed"] == seed and result["network"] == network,
        "Runner metadata mismatch",
    )

    verify_case(
        solver,
        case,
        pipeline_result=result,
    )


# =========================================================
# VERIFICATION RUNNER
# =========================================================


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--solver",
        type=Path,
        required=True,
        help="Current experiment scenario_solver.py",
    )

    args = parser.parse_args()

    path = args.solver.resolve()

    print(f"Solver: {path}")

    print(f"SHA256: {hashlib.sha256(path.read_bytes()).hexdigest()}")

    spec = importlib.util.spec_from_file_location(
        "experiment_solver",
        path,
    )

    solver = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(solver)

    count = 0

    try:
        for case in list(fixed_cases()) + list(random_cases()):
            verify_case(
                solver,
                case,
            )
            count += 1

        for network in ["33", "118"]:
            for seed in [0, 1]:
                verify_runner(
                    solver,
                    network,
                    seed,
                )
                count += 1

        print(
            f"\nALL {count} CASES PASSED (five formulations per case)."
        )
    finally:
        solver.gp.disposeDefaultEnv()


if __name__ == "__main__":
    main()
