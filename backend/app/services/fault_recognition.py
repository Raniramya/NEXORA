from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC


class XGBoostLabelClassifier(BaseEstimator, ClassifierMixin):
    """Encode string fault labels while preserving sklearn's classifier contract."""

    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed

    def fit(self, X, y):
        from xgboost import XGBClassifier

        self.label_encoder_ = LabelEncoder().fit(y)
        self.classes_ = self.label_encoder_.classes_
        self.model_ = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.08, random_state=self.random_seed, eval_metric="mlogloss")
        self.model_.fit(X, self.label_encoder_.transform(y))
        return self

    def predict(self, X):
        return self.label_encoder_.inverse_transform(self.model_.predict(X).astype(int))

    def predict_proba(self, X):
        return self.model_.predict_proba(X)


def _xgboost(seed: int):
    try:
        import xgboost  # noqa: F401
    except ImportError:
        return None
    return XGBoostLabelClassifier(random_seed=seed)


def train_fault_models(
    rows: list[dict[str, float]],
    labels: list[str],
    *,
    artifact_dir: Path,
    random_seed: int = 42,
    test_size: float = 0.25,
) -> tuple[dict[str, Any], str, list[str], list[str], str]:
    if len(rows) != len(labels) or len(rows) < 8:
        raise ValueError("At least 8 labelled feature sets are required.")
    class_names, counts = np.unique(labels, return_counts=True)
    if len(class_names) < 2:
        raise ValueError("At least two fault classes are required.")
    if int(np.min(counts)) < 2:
        raise ValueError("Each fault class requires at least two labelled windows.")
    feature_names = sorted(set.intersection(*(set(row) for row in rows)))
    if not feature_names:
        raise ValueError("Labelled windows have no common numerical features.")
    X = np.asarray([[row[name] for name in feature_names] for row in rows], dtype=np.float64)
    y = np.asarray(labels)
    if not np.all(np.isfinite(X)):
        raise ValueError("Training features must be finite.")
    X_development, X_calibration, y_development, y_calibration = train_test_split(X, y, test_size=test_size, random_state=random_seed, stratify=y)
    validation_fraction = test_size / (1 - test_size)
    X_train, X_test, y_train, y_test = train_test_split(X_development, y_development, test_size=validation_fraction, random_state=random_seed, stratify=y_development)
    candidates: dict[str, Any] = {
        "random_forest": RandomForestClassifier(n_estimators=200, random_state=random_seed, class_weight="balanced"),
        "svm_rbf": Pipeline([("scale", StandardScaler()), ("model", SVC(probability=True, class_weight="balanced", random_state=random_seed))]),
    }
    unavailable: dict[str, str] = {}
    xgb = _xgboost(random_seed)
    if xgb is None:
        unavailable["xgboost"] = "dependency_not_installed"
    else:
        candidates["xgboost"] = xgb

    results: dict[str, dict[str, Any]] = {}
    fitted: dict[str, Any] = {}
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        predicted = model.predict(X_test)
        results[name] = {
            "accuracy": float(accuracy_score(y_test, predicted)),
            "precision_weighted": float(precision_score(y_test, predicted, average="weighted", zero_division=0)),
            "recall_weighted": float(recall_score(y_test, predicted, average="weighted", zero_division=0)),
            "f1_weighted": float(f1_score(y_test, predicted, average="weighted", zero_division=0)),
            "confusion_matrix": confusion_matrix(y_test, predicted, labels=class_names).tolist(),
        }
        fitted[name] = model
    winner = max(results, key=lambda name: results[name]["f1_weighted"])
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "fault_model.joblib"
    background = X_train[: min(50, len(X_train))]
    joblib.dump({"model": fitted[winner], "feature_names": feature_names, "class_names": class_names.tolist(), "background": background, "calibration_features": X_calibration, "calibration_labels": y_calibration}, artifact_path)
    summary = {"models": results, "unavailable_models": unavailable, "train_size": len(X_train), "test_size": len(X_test), "validation_size": len(X_test), "calibration_size": len(X_calibration), "split": "seeded_stratified_train_validation_calibration"}
    return summary, winner, feature_names, class_names.tolist(), str(artifact_path)


def predict_fault(artifact_location: str, features: dict[str, float]) -> tuple[str, float | None, dict[str, float]]:
    artifact = joblib.load(artifact_location)
    names = artifact["feature_names"]
    missing = [name for name in names if name not in features]
    if missing:
        raise ValueError(f"Feature set is missing required features: {', '.join(missing)}")
    X = np.asarray([[features[name] for name in names]], dtype=np.float64)
    model = artifact["model"]
    predicted = str(model.predict(X)[0])
    probabilities: dict[str, float] = {}
    confidence = None
    if hasattr(model, "predict_proba"):
        values = model.predict_proba(X)[0]
        probabilities = {str(name): float(value) for name, value in zip(model.classes_, values)}
        confidence = max(probabilities.values())
    return predicted, confidence, probabilities
