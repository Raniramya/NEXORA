from __future__ import annotations

from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate_maintenance_effect(
    records: list[dict[str, Any]],
    *,
    confounders: list[str],
    dag_edges: list[list[str]],
    minimum_samples: int = 20,
) -> dict[str, Any]:
    graph = nx.DiGraph()
    graph.add_edges_from((edge[0], edge[1]) for edge in dag_edges)
    if not nx.is_directed_acyclic_graph(graph):
        return {"validity_status": "abstained", "abstention_reason": "causal_dag_is_cyclic", "estimated_effect": None}
    treatment, outcome = "treatment_applied", "outcome_change"
    if treatment not in graph.nodes or outcome not in graph.nodes:
        return {"validity_status": "abstained", "abstention_reason": "dag_missing_treatment_or_outcome", "estimated_effect": None}
    common_causes = (nx.ancestors(graph, treatment) & nx.ancestors(graph, outcome)) - {treatment, outcome}
    missing_confounders = sorted(common_causes - set(confounders))
    descendants = sorted(set(confounders) & nx.descendants(graph, treatment))
    if missing_confounders:
        return {"validity_status": "abstained", "abstention_reason": "unadjusted_common_causes", "missing_confounders": missing_confounders, "estimated_effect": None}
    if descendants:
        return {"validity_status": "abstained", "abstention_reason": "adjustment_includes_treatment_descendant", "invalid_adjustments": descendants, "estimated_effect": None}
    if len(records) < minimum_samples:
        return {"validity_status": "abstained", "abstention_reason": "insufficient_confirmed_experiments", "sample_size": len(records), "minimum_samples": minimum_samples, "estimated_effect": None}

    rows = []
    for record in records:
        row = {treatment: int(record[treatment]), outcome: float(record["post_outcome"] - record["pre_outcome"])}
        covariates = record.get("covariates", {})
        if any(name not in covariates for name in confounders):
            continue
        row.update({name: covariates[name] for name in confounders})
        rows.append(row)
    frame = pd.DataFrame(rows).dropna()
    if len(frame) < minimum_samples:
        return {"validity_status": "abstained", "abstention_reason": "insufficient_complete_cases", "sample_size": len(frame), "minimum_samples": minimum_samples, "estimated_effect": None}
    counts = frame[treatment].value_counts().to_dict()
    if set(counts) != {0, 1} or min(counts.values()) < 5:
        return {"validity_status": "abstained", "abstention_reason": "insufficient_treatment_overlap", "group_counts": {str(key): int(value) for key, value in counts.items()}, "estimated_effect": None}
    numeric = frame[[treatment, outcome, *confounders]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric) < minimum_samples:
        return {"validity_status": "abstained", "abstention_reason": "non_numeric_or_missing_confounders", "sample_size": len(numeric), "estimated_effect": None}
    X = sm.add_constant(numeric[[treatment, *confounders]], has_constant="add")
    fit = sm.OLS(numeric[outcome], X).fit(cov_type="HC3")
    interval = fit.conf_int().loc[treatment].tolist()
    treated_mean = float(numeric.loc[numeric[treatment] == 1, outcome].mean())
    control_mean = float(numeric.loc[numeric[treatment] == 0, outcome].mean())
    return {
        "validity_status": "estimated_with_assumptions",
        "abstention_reason": None,
        "estimated_effect": float(fit.params[treatment]),
        "confidence_interval": [float(interval[0]), float(interval[1])],
        "p_value": float(fit.pvalues[treatment]),
        "sample_size": int(len(numeric)),
        "group_counts": {"control": int((numeric[treatment] == 0).sum()), "treated": int((numeric[treatment] == 1).sum())},
        "diagnostics": {"unadjusted_mean_difference": treated_mean - control_mean, "note": "Unadjusted difference is diagnostic association, not the causal estimate."},
        "estimand": "Average effect of applying the maintenance intervention on post-minus-pre outcome change",
        "estimator": "ols_backdoor_adjustment_hc3",
        "assumptions": ["DAG is correctly specified", "provided covariates block measured backdoor paths", "no unmeasured confounding", "treatment overlap", "linear conditional outcome model"],
        "dag": {"nodes": list(graph.nodes), "edges": [[left, right] for left, right in graph.edges]},
        "confounders": confounders,
    }


def maintenance_counterfactual(study_result: dict[str, Any], *, current_outcome: float, apply_intervention: bool, feasible: bool, infeasibility_reason: str | None, lower_is_better: bool) -> dict[str, Any]:
    if study_result.get("validity_status") != "estimated_with_assumptions" or study_result.get("estimated_effect") is None:
        return {"status": "abstained", "abstention_reason": "causal_study_not_identified", "estimated_outcome": None}
    if not feasible:
        return {"status": "abstained", "abstention_reason": infeasibility_reason or "intervention_not_feasible", "estimated_outcome": None}
    effect = float(study_result["estimated_effect"]) if apply_intervention else 0.0
    interval = study_result.get("confidence_interval")
    outcome_interval = [current_outcome + float(interval[0]), current_outcome + float(interval[1])] if apply_intervention and interval else None
    return {
        "status": "estimated_with_assumptions",
        "kind": "causal_counterfactual",
        "current_outcome": current_outcome,
        "apply_intervention": apply_intervention,
        "estimated_outcome": current_outcome + effect,
        "estimated_change": effect,
        "estimated_benefit": -effect if lower_is_better else effect,
        "outcome_interval": outcome_interval,
        "warning": "Model-based causal estimate conditional on the study assumptions; not an observed post-maintenance result.",
    }
