from __future__ import annotations

from typing import Any

import numpy as np


OBJECTIVES = ["residual_risk", "cost", "downtime_hours", "travel_km", "negative_causal_benefit"]


def _objectives(genome: np.ndarray, candidates: list[dict[str, Any]]) -> list[float]:
    selected = [candidate for bit, candidate in zip(genome, candidates) if bit]
    return [
        float(sum(candidate["risk"] for bit, candidate in zip(genome, candidates) if not bit)),
        float(sum(candidate["cost"] for candidate in selected)),
        float(sum(candidate["downtime_hours"] for candidate in selected)),
        float(sum(candidate["distance_km"] for candidate in selected)),
        float(-sum(candidate["causal_benefit"] for candidate in selected)),
    ]


def _feasible(genome: np.ndarray, candidates: list[dict[str, Any]], constraints: dict[str, float | int]) -> bool:
    selected = [candidate for bit, candidate in zip(genome, candidates) if bit]
    return (
        len(selected) <= constraints["max_actions"]
        and sum(item["cost"] for item in selected) <= constraints["budget"] + 1e-9
        and sum(item["downtime_hours"] for item in selected) <= constraints["max_downtime_hours"] + 1e-9
        and sum(item["duration_hours"] for item in selected) <= constraints["technician_hours"] + 1e-9
    )


def _repair(genome: np.ndarray, candidates: list[dict[str, Any]], constraints: dict[str, float | int]) -> np.ndarray:
    repaired = genome.copy()
    while not _feasible(repaired, candidates, constraints):
        selected = np.flatnonzero(repaired)
        if not len(selected):
            break
        weakest = min(selected, key=lambda index: (
            candidates[index]["risk"] + candidates[index]["causal_benefit"]
        ) / max(candidates[index]["cost"] + candidates[index]["downtime_hours"] + candidates[index]["duration_hours"], 1e-9))
        repaired[weakest] = 0
    return repaired


def _dominates(left: np.ndarray, right: np.ndarray) -> bool:
    return bool(np.all(left <= right) and np.any(left < right))


def _fronts(values: np.ndarray) -> list[list[int]]:
    dominates: list[list[int]] = [[] for _ in values]
    dominated_count = np.zeros(len(values), dtype=int)
    fronts = [[]]
    for left in range(len(values)):
        for right in range(len(values)):
            if left == right:
                continue
            if _dominates(values[left], values[right]):
                dominates[left].append(right)
            elif _dominates(values[right], values[left]):
                dominated_count[left] += 1
        if dominated_count[left] == 0:
            fronts[0].append(left)
    level = 0
    while fronts[level]:
        following = []
        for left in fronts[level]:
            for right in dominates[left]:
                dominated_count[right] -= 1
                if dominated_count[right] == 0:
                    following.append(right)
        level += 1
        fronts.append(following)
    return fronts[:-1]


def _crowding(front: list[int], values: np.ndarray) -> dict[int, float]:
    distance = {index: 0.0 for index in front}
    if len(front) <= 2:
        return {index: float("inf") for index in front}
    for objective in range(values.shape[1]):
        ordered = sorted(front, key=lambda index: values[index, objective])
        distance[ordered[0]] = distance[ordered[-1]] = float("inf")
        span = values[ordered[-1], objective] - values[ordered[0], objective]
        if span > 0:
            for position in range(1, len(ordered) - 1):
                distance[ordered[position]] += float((values[ordered[position + 1], objective] - values[ordered[position - 1], objective]) / span)
    return distance


def _select(population: np.ndarray, values: np.ndarray, size: int) -> np.ndarray:
    selected = []
    for front in _fronts(values):
        if len(selected) + len(front) <= size:
            selected.extend(front)
        else:
            crowding = _crowding(front, values)
            selected.extend(sorted(front, key=lambda index: crowding[index], reverse=True)[:size - len(selected)])
            break
    return population[selected]


def _solution(genome: np.ndarray, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    objectives = _objectives(genome, candidates)
    selected = [candidate for bit, candidate in zip(genome, candidates) if bit]
    return {
        "selected_candidate_ids": [item["candidate_id"] for item in selected],
        "selected_machine_ids": [item["machine_id"] for item in selected],
        "objectives": dict(zip(OBJECTIVES, objectives)),
        "resource_usage": {
            "action_count": len(selected),
            "technician_hours": float(sum(item["duration_hours"] for item in selected)),
        },
    }


def _baseline(candidates: list[dict[str, Any]], constraints: dict[str, float | int], key) -> dict[str, Any]:
    genome = np.zeros(len(candidates), dtype=np.int8)
    for index in sorted(range(len(candidates)), key=key, reverse=True):
        proposal = genome.copy()
        proposal[index] = 1
        if _feasible(proposal, candidates, constraints):
            genome = proposal
    return _solution(genome, candidates)


def optimize_maintenance_schedule(
    candidates: list[dict[str, Any]], constraints: dict[str, float | int], *,
    population_size: int = 80, generations: int = 100, random_seed: int = 42,
) -> dict[str, Any]:
    if not candidates:
        return {"status": "abstained", "abstention_reason": "no_eligible_evidence_backed_candidates", "pareto_solutions": [], "baselines": {}}
    if population_size < 4 or generations < 1:
        raise ValueError("NSGA-II requires population_size >= 4 and generations >= 1.")
    rng = np.random.default_rng(random_seed)
    population = rng.integers(0, 2, size=(population_size, len(candidates)), dtype=np.int8)
    population[0] = 0
    population = np.asarray([_repair(genome, candidates, constraints) for genome in population])
    for _ in range(generations):
        offspring = []
        while len(offspring) < population_size:
            left, right = population[rng.integers(len(population), size=2)]
            mask = rng.random(len(candidates)) < 0.5
            child = np.where(mask, left, right).astype(np.int8)
            child[rng.random(len(candidates)) < (1 / len(candidates))] ^= 1
            offspring.append(_repair(child, candidates, constraints))
        combined = np.vstack([population, offspring])
        values = np.asarray([_objectives(genome, candidates) for genome in combined])
        population = _select(combined, values, population_size)
    unique = np.unique(population, axis=0)
    values = np.asarray([_objectives(genome, candidates) for genome in unique])
    pareto = [_solution(unique[index], candidates) for index in _fronts(values)[0]]
    pareto.sort(key=lambda item: (item["objectives"]["residual_risk"], item["objectives"]["cost"]))
    baselines = {
        "greedy_risk_cost": _baseline(candidates, constraints, lambda index: candidates[index]["risk"] / max(candidates[index]["cost"], 1e-9)),
        "conventional_risk_priority": _baseline(candidates, constraints, lambda index: candidates[index]["risk"]),
    }
    baseline_comparison = {}
    for name, baseline in baselines.items():
        baseline_values = np.asarray(list(baseline["objectives"].values()))
        dominating = sum(_dominates(np.asarray(list(solution["objectives"].values())), baseline_values) for solution in pareto)
        baseline_comparison[name] = {"pareto_solutions_dominating_baseline": int(dominating), "baseline_is_pareto_member": baseline in pareto}
    return {
        "status": "completed",
        "method": "binary_nsga_ii",
        "objective_directions": {name: "minimize" for name in OBJECTIVES},
        "pareto_solutions": pareto,
        "baselines": baselines,
        "baseline_comparison": baseline_comparison,
        "eligible_candidate_count": len(candidates),
        "warning": "Pareto solutions are evidence-bounded planning options and require human review; they do not authorize maintenance.",
    }
