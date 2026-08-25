from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, davies_bouldin_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def _pipeline(frame: pd.DataFrame) -> tuple[ColumnTransformer, list[str]]:
    numeric = frame.select_dtypes(include=np.number).columns.tolist()
    categorical = [column for column in frame.columns if column not in numeric]
    return ColumnTransformer([("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric), ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical)]), numeric


def run_ml(frame: pd.DataFrame, config: dict, artifact_dir: Path) -> tuple[dict[str, Any], str | None]:
    task, target = config["task"], config.get("target")
    features = config.get("features") or [column for column in frame.columns if column != target]
    if task not in {"clustering", "anomaly_detection"} and (not target or target not in frame): raise ValueError("A valid target is required.")
    X = frame[features].copy(); seed = config.get("random_seed", 42)
    if task in {"clustering", "anomaly_detection"}:
        prepared, _ = _pipeline(X); transformed = prepared.fit_transform(X)
        if task == "clustering":
            model = KMeans(n_clusters=min(3, max(2, len(X) // 10)), random_state=seed, n_init=10); labels = model.fit_predict(transformed)
            metrics = {"silhouette": float(silhouette_score(transformed, labels)) if len(set(labels)) > 1 else None, "davies_bouldin": float(davies_bouldin_score(transformed, labels)) if len(set(labels)) > 1 else None}
            result = {"winning_model": "kmeans", "metrics": metrics, "labels": labels.tolist()}
        else:
            model = IsolationForest(random_state=seed, contamination="auto"); labels = model.fit_predict(transformed); scores = -model.score_samples(transformed)
            result = {"winning_model": "isolation_forest", "metrics": {}, "anomaly_scores": scores.tolist(), "predicted_anomalies": (labels == -1).tolist()}
        artifact_dir.mkdir(parents=True, exist_ok=True); path = artifact_dir / "model.joblib"; joblib.dump((prepared, model), path); return result, str(path)
    y = frame[target]; stratify = y if task in {"binary_classification", "multiclass_classification"} and y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=config.get("test_size", .2), random_state=seed, stratify=stratify)
    prepared, _ = _pipeline(X)
    if task in {"regression", "forecasting"}:
        candidates = {"linear_regression": LinearRegression(), "random_forest": RandomForestRegressor(n_estimators=100, random_state=seed)}
        metric = lambda actual, pred: {"mae": float(mean_absolute_error(actual, pred)), "rmse": float(mean_squared_error(actual, pred) ** .5), "r2": float(r2_score(actual, pred))}
        higher = "r2"
    else:
        candidates = {"logistic_regression": LogisticRegression(max_iter=1000, random_state=seed), "random_forest": RandomForestClassifier(n_estimators=100, random_state=seed)}
        def metric(actual, pred, probabilities=None):
            values = {"accuracy": float(accuracy_score(actual, pred)), "precision": float(precision_score(actual, pred, average="weighted", zero_division=0)), "recall": float(recall_score(actual, pred, average="weighted", zero_division=0)), "f1": float(f1_score(actual, pred, average="weighted", zero_division=0))}
            if probabilities is not None and len(np.unique(actual)) == 2: values["roc_auc"] = float(roc_auc_score(actual, probabilities[:, 1]))
            return values
        higher = "f1"
    results, fitted = {}, {}
    for name, model in candidates.items():
        pipeline = Pipeline([("preprocess", prepared), ("model", model)]); pipeline.fit(X_train, y_train); pred = pipeline.predict(X_test)
        probabilities = pipeline.predict_proba(X_test) if hasattr(pipeline, "predict_proba") else None
        results[name] = metric(y_test, pred) if task in {"regression", "forecasting"} else metric(y_test, pred, probabilities); fitted[name] = pipeline
    winner = max(results, key=lambda name: results[name][higher])
    importance = getattr(fitted[winner]["model"], "feature_importances_", None)
    artifact_dir.mkdir(parents=True, exist_ok=True); path = artifact_dir / "model.joblib"; joblib.dump(fitted[winner], path)
    return {"winning_model": winner, "models": results, "metrics": results[winner], "feature_importance": importance.tolist() if importance is not None else [], "train_size": len(X_train), "test_size": len(X_test)}, str(path)
