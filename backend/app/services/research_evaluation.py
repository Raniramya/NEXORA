from __future__ import annotations

import hashlib
import json
from math import sqrt
from pathlib import Path
from typing import Any

import numpy as np


REQUIRED_BASELINES = {"integrated", "traditional_analytics", "predictive_ml_only", "llm_only"}


def physical_trial_result(*, pre_value: float, post_value: float, predicted_benefit: float, lower_is_better: bool) -> dict[str, Any]:
    observed_change = float(post_value - pre_value)
    observed_benefit = float(-observed_change if lower_is_better else observed_change)
    return {
        "pre_value": float(pre_value), "post_value": float(post_value), "observed_change": observed_change,
        "predicted_benefit": float(predicted_benefit), "observed_benefit": observed_benefit,
        "signed_prediction_error": float(predicted_benefit - observed_benefit),
        "absolute_error": float(abs(predicted_benefit - observed_benefit)),
        "lower_is_better": lower_is_better,
        "interpretation": "Observed benefit is computed from linked physical pre/post measurements; predicted benefit remains a prior model-based causal estimate.",
    }


def _mean_interval(values: np.ndarray) -> list[float] | None:
    if len(values) < 2:
        return None
    margin = 1.96 * float(values.std(ddof=1)) / sqrt(len(values))
    mean = float(values.mean())
    return [mean - margin, mean + margin]


def summarize_physical_trials(trials: list[dict[str, Any]], minimum_trials: int = 3) -> dict[str, Any]:
    if len(trials) < minimum_trials:
        return {"status": "abstained", "abstention_reason": "insufficient_confirmed_physical_trials", "trial_count": len(trials), "minimum_trials": minimum_trials}
    errors = np.asarray([float(item["predicted_benefit"] - item["observed_benefit"]) for item in trials])
    absolute = np.abs(errors)
    return {
        "status": "completed", "trial_count": len(trials),
        "mean_absolute_error": float(absolute.mean()), "root_mean_squared_error": float(np.sqrt(np.mean(errors ** 2))),
        "mean_signed_error": float(errors.mean()), "mean_signed_error_95_normal_interval": _mean_interval(errors),
        "predicted_mean_benefit": float(np.mean([item["predicted_benefit"] for item in trials])),
        "observed_mean_benefit": float(np.mean([item["observed_benefit"] for item in trials])),
        "metric_definitions": {
            "mean_absolute_error": "Mean absolute difference between persisted predicted causal benefit and benefit computed from physical pre/post readings.",
            "root_mean_squared_error": "Square root of mean squared predicted-minus-observed benefit error.",
        },
    }


def _wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.96
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total) / denominator
    return [center - margin, center + margin]


def _variant_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    answered = [row for row in rows if row["recommendation_made"]]
    correct = [row for row in answered if row.get("predicted_action") == row["ground_truth_action"]]
    harmful = [row for row in answered if row["observed_harm"]]
    provenance = [row for row in rows if row.get("provenance_references")]
    uncertainty = [row for row in rows if row["uncertainty_handled"]]
    return {
        "case_count": total, "answered_count": len(answered),
        "coverage": len(answered) / total, "abstention_rate": 1 - len(answered) / total,
        "selective_accuracy": len(correct) / len(answered) if answered else None,
        "overall_correct_rate": len(correct) / total,
        "harmful_recommendation_rate": len(harmful) / len(answered) if answered else None,
        "provenance_coverage": len(provenance) / total,
        "uncertainty_handling_rate": len(uncertainty) / total,
        "selective_accuracy_95_wilson_interval": _wilson(len(correct), len(answered)),
        "harmful_recommendation_95_wilson_interval": _wilson(len(harmful), len(answered)),
        "failure_case_ids": [row["case_id"] for row in answered if row.get("predicted_action") != row["ground_truth_action"] or row["observed_harm"]],
    }


def evaluate_benchmark(observations: list[dict[str, Any]], minimum_aligned_cases: int = 3) -> dict[str, Any]:
    variants = sorted({row["system_variant"] for row in observations})
    missing = sorted(REQUIRED_BASELINES - set(variants))
    cases_by_variant = {variant: {row["case_id"] for row in observations if row["system_variant"] == variant} for variant in variants}
    aligned = sorted(set.intersection(*(cases_by_variant[variant] for variant in REQUIRED_BASELINES))) if not missing else []
    if missing or len(aligned) < minimum_aligned_cases:
        return {
            "status": "abstained", "abstention_reason": "incomplete_baseline_design" if missing else "insufficient_aligned_cases",
            "missing_required_variants": missing, "aligned_case_count": len(aligned), "minimum_aligned_cases": minimum_aligned_cases,
        }
    aligned_set = set(aligned)
    metrics = {variant: _variant_metrics([row for row in observations if row["system_variant"] == variant and row["case_id"] in aligned_set]) for variant in variants}
    integrated = metrics["integrated"]
    deltas = {}
    for variant, values in metrics.items():
        if variant == "integrated":
            continue
        deltas[variant] = {
            name: (integrated[name] - values[name]) if integrated[name] is not None and values[name] is not None else None
            for name in ("coverage", "selective_accuracy", "overall_correct_rate", "harmful_recommendation_rate", "provenance_coverage", "uncertainty_handling_rate")
        }
    return {
        "status": "completed", "aligned_case_ids": aligned, "aligned_case_count": len(aligned),
        "variant_metrics": metrics, "integrated_minus_variant": deltas,
        "metric_definitions": {
            "coverage": "Fraction of aligned cases receiving a recommendation.",
            "selective_accuracy": "Correct action fraction among cases receiving a recommendation.",
            "overall_correct_rate": "Correct recommendations divided by all aligned cases, including abstentions.",
            "harmful_recommendation_rate": "Observed harmful outcomes divided by recommendations made.",
            "provenance_coverage": "Fraction of cases with at least one recorded evidence reference.",
            "uncertainty_handling_rate": "Fraction of cases whose recorded output explicitly handled uncertainty or abstention.",
        },
    }


def write_reproducible_report(artifact_dir: Path, run_id: str, payload: dict[str, Any]) -> tuple[str, str]:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{run_id}.json"
    path.write_text(json.dumps({**payload, "artifact_sha256": digest}, indent=2, sort_keys=True), encoding="utf-8")
    return str(path), digest
