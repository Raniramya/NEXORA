from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression


def _normalize(values: np.ndarray) -> np.ndarray:
    totals = values.sum(axis=1, keepdims=True)
    return values / np.where(totals == 0, 1, totals)


def _metrics(probabilities: np.ndarray, labels: np.ndarray, classes: list[str], bins: int = 10) -> dict[str, Any]:
    indices = np.asarray([classes.index(str(label)) for label in labels])
    one_hot = np.eye(len(classes))[indices]
    confidence = probabilities.max(axis=1)
    correct = probabilities.argmax(axis=1) == indices
    ece = 0.0
    rows = []
    for lower, upper in zip(np.linspace(0, 1, bins + 1)[:-1], np.linspace(0, 1, bins + 1)[1:]):
        mask = (confidence >= lower) & ((confidence < upper) if upper < 1 else (confidence <= upper))
        if mask.any():
            bin_confidence, bin_accuracy = float(confidence[mask].mean()), float(correct[mask].mean())
            ece += float(mask.mean()) * abs(bin_confidence - bin_accuracy)
            rows.append({"lower": float(lower), "upper": float(upper), "confidence": bin_confidence, "accuracy": bin_accuracy, "count": int(mask.sum())})
    return {"multiclass_brier": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))), "expected_calibration_error": float(ece), "accuracy": float(correct.mean()), "bins": rows}


def fit_reliability_model(fault_artifact_location: str, *, artifact_dir: Path, alpha: float = 0.1, minimum_calibration_size: int = 20) -> tuple[str, dict[str, Any], str | None]:
    artifact = joblib.load(fault_artifact_location)
    X = np.asarray(artifact.get("calibration_features"), dtype=np.float64)
    y = np.asarray(artifact.get("calibration_labels"))
    classes = [str(value) for value in artifact["model"].classes_]
    if X.ndim != 2 or len(X) < minimum_calibration_size:
        return "abstained", {"abstention_reason": "insufficient_independent_calibration_evidence", "calibration_size": len(X) if X.ndim else 0, "minimum_calibration_size": minimum_calibration_size}, None
    if set(map(str, np.unique(y))) != set(classes):
        return "abstained", {"abstention_reason": "calibration_partition_missing_classes", "observed_classes": list(map(str, np.unique(y))), "required_classes": classes}, None
    raw = np.asarray(artifact["model"].predict_proba(X), dtype=np.float64)
    calibrators = []
    calibrated_columns = []
    for index, class_name in enumerate(classes):
        target = (y.astype(str) == class_name).astype(int)
        if min(np.bincount(target, minlength=2)) < 2:
            return "abstained", {"abstention_reason": "insufficient_per_class_calibration_evidence", "class": class_name}, None
        logits = np.log(np.clip(raw[:, index], 1e-6, 1 - 1e-6) / np.clip(1 - raw[:, index], 1e-6, 1))[:, None]
        calibrator = LogisticRegression(random_state=42).fit(logits, target)
        calibrators.append(calibrator)
        calibrated_columns.append(calibrator.predict_proba(logits)[:, 1])
    calibrated = _normalize(np.column_stack(calibrated_columns))
    label_indices = np.asarray([classes.index(str(label)) for label in y])
    nonconformity = 1 - calibrated[np.arange(len(y)), label_indices]
    quantile_level = min(1.0, np.ceil((len(y) + 1) * (1 - alpha)) / len(y))
    quantile = float(np.quantile(nonconformity, quantile_level, method="higher"))
    prediction_sets = calibrated >= (1 - quantile)
    coverage = float(prediction_sets[np.arange(len(y)), label_indices].mean())
    artifact_dir.mkdir(parents=True, exist_ok=True)
    output = artifact_dir / "reliability_model.joblib"
    joblib.dump({"calibrators": calibrators, "classes": classes, "conformal_quantile": quantile, "alpha": alpha, "fault_artifact_location": fault_artifact_location}, output)
    results = {"calibration_size": len(y), "alpha": alpha, "raw_metrics": _metrics(raw, y, classes), "calibrated_metrics": _metrics(calibrated, y, classes), "conformal_quantile": quantile, "empirical_calibration_coverage": coverage, "mean_prediction_set_size": float(prediction_sets.sum(axis=1).mean())}
    return "calibrated", results, str(output)


def evaluate_selective_prediction(reliability_artifact_location: str, features: dict[str, float], *, anomaly_is_ood: bool, act_threshold: float = 0.8, monitor_threshold: float = 0.5) -> dict[str, Any]:
    reliability = joblib.load(reliability_artifact_location)
    fault = joblib.load(reliability["fault_artifact_location"])
    names, model = fault["feature_names"], fault["model"]
    missing = [name for name in names if name not in features]
    if missing:
        raise ValueError(f"Feature set is missing required features: {', '.join(missing)}")
    X = np.asarray([[features[name] for name in names]], dtype=np.float64)
    raw = np.asarray(model.predict_proba(X), dtype=np.float64)
    columns = []
    for index, calibrator in enumerate(reliability["calibrators"]):
        logits = np.log(np.clip(raw[:, index], 1e-6, 1 - 1e-6) / np.clip(1 - raw[:, index], 1e-6, 1))[:, None]
        columns.append(calibrator.predict_proba(logits)[:, 1])
    calibrated = _normalize(np.column_stack(columns))[0]
    classes = reliability["classes"]
    prediction_set = [class_name for class_name, probability in zip(classes, calibrated) if probability >= 1 - reliability["conformal_quantile"]]
    probabilities = {class_name: float(probability) for class_name, probability in zip(classes, calibrated)}
    maximum = float(calibrated.max())
    if anomaly_is_ood:
        action, reasons = "ABSTAIN", ["Input is outside the learned normal envelope."]
    elif len(prediction_set) == 1 and maximum >= act_threshold:
        action, reasons = "ACT", []
    elif prediction_set and maximum >= monitor_threshold:
        action, reasons = "MONITOR", ["Prediction remains ambiguous or below the ACT threshold."]
    else:
        action, reasons = "ABSTAIN", ["Calibrated evidence is too weak for selective prediction."]
    return {"action": action, "reasons": reasons, "calibrated_probabilities": probabilities, "prediction_set": prediction_set, "maximum_calibrated_probability": maximum, "anomaly_is_ood": anomaly_is_ood, "policy": {"act_threshold": act_threshold, "monitor_threshold": monitor_threshold}, "interpretation": "ACT accepts a fault classification for downstream review; it is not authorization to perform maintenance."}
