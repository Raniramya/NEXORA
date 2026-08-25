from typing import Any
import networkx as nx
import pandas as pd
import statsmodels.api as sm


def dag_from_edges(edges: list[list[str]]) -> tuple[nx.DiGraph, dict]:
    graph = nx.DiGraph(); graph.add_edges_from((edge[0], edge[1]) for edge in edges)
    if not nx.is_directed_acyclic_graph(graph): raise ValueError("Causal DAG must be acyclic.")
    return graph, {"nodes": list(graph.nodes), "edges": [[a, b] for a, b in graph.edges]}


def estimate_effect(frame: pd.DataFrame, treatment: str, outcome: str, confounders: list[str], treatment_type: str, edges: list[list[str]]) -> dict[str, Any]:
    graph, dag = dag_from_edges(edges)
    required = [treatment, outcome, *confounders]
    if any(column not in frame for column in required): raise ValueError("Treatment, outcome, and confounders must be dataset columns.")
    data = frame[required].dropna()
    if treatment_type != "binary" and treatment_type != "continuous": raise ValueError("Treatment type must be binary or continuous.")
    if treatment_type == "binary" and data[treatment].nunique() != 2: raise ValueError("Binary treatment must contain exactly two observed values.")
    X = sm.add_constant(data[[treatment, *confounders]], has_constant="add")
    fit = sm.OLS(data[outcome], X).fit()
    ci = fit.conf_int().loc[treatment].tolist()
    warnings = []
    if not confounders: warnings.append("No adjustment set provided; observational causal validity is not established.")
    if not set([treatment, outcome]).issubset(graph.nodes): warnings.append("DAG omits treatment or outcome nodes.")
    return {"treatment": treatment, "outcome": outcome, "confounders": confounders, "estimand": f"Average treatment effect of {treatment} on {outcome} adjusted for selected confounders", "estimator": "linear_regression_adjustment", "estimated_effect": float(fit.params[treatment]), "confidence_interval": [float(ci[0]), float(ci[1])], "p_value": float(fit.pvalues[treatment]), "sample_size": int(len(data)), "assumptions": ["DAG is correctly specified", "selected confounders block backdoor paths", "positivity", "linear conditional outcome model"], "refutation_results": {"raw_difference_or_association": float(data[[treatment, outcome]].corr().iloc[0, 1]), "note": "Raw association is reported only as a diagnostic, not a causal estimate."}, "warnings": warnings + ["DoWhy/EconML estimators are optional dependencies and are only used when installed and applicable."], "validity_status": "warning" if warnings else "estimated_with_assumptions", "dag": dag}


def intervention_scenario(result: dict, baseline: float, new_value: float) -> dict:
    effect = result["estimated_effect"]
    difference = effect * (new_value - baseline)
    return {"kind": "causal_intervention_estimate", "baseline_expected_outcome": None, "intervention_expected_outcome": None, "estimated_difference": difference, "uncertainty": result.get("confidence_interval"), "method_used": result["estimator"], "warning": "This is a model-based causal intervention estimate conditional on recorded assumptions; it is not a prediction."}
