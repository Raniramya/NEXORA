from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def train_anomaly_model(rows: list[dict[str, float]], *, artifact_dir: Path, random_seed: int = 42, contamination: float = 0.05) -> tuple[dict[str, Any], list[str], str]:
    if len(rows) < 8:
        raise ValueError("At least 8 confirmed normal windows are required.")
    feature_names = sorted(set.intersection(*(set(row) for row in rows)))
    if not feature_names:
        raise ValueError("Normal windows have no common numerical features.")
    X = np.asarray([[row[name] for name in feature_names] for row in rows], dtype=np.float64)
    if not np.all(np.isfinite(X)):
        raise ValueError("Anomaly training features must be finite.")
    model = Pipeline([("scale", StandardScaler()), ("model", IsolationForest(n_estimators=200, contamination=contamination, random_state=random_seed))])
    model.fit(X)
    decisions = model.decision_function(X)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "anomaly_model.joblib"
    joblib.dump({"model": model, "feature_names": feature_names}, artifact_path)
    return {
        "training_size": len(X),
        "decision_score_min": float(np.min(decisions)),
        "decision_score_max": float(np.max(decisions)),
        "decision_score_mean": float(np.mean(decisions)),
        "interpretation": "Negative decision scores are flagged as unknown-condition anomalies.",
    }, feature_names, str(artifact_path)


def score_anomaly(artifact_location: str, features: dict[str, float]) -> tuple[float, bool]:
    artifact = joblib.load(artifact_location)
    names = artifact["feature_names"]
    missing = [name for name in names if name not in features]
    if missing:
        raise ValueError(f"Feature set is missing required features: {', '.join(missing)}")
    X = np.asarray([[features[name] for name in names]], dtype=np.float64)
    model = artifact["model"]
    decision_score = float(model.decision_function(X)[0])
    return decision_score, decision_score < 0
