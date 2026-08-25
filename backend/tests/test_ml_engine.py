import numpy as np
import pandas as pd

from app.services.ml_engine import run_ml


def data() -> pd.DataFrame:
    rng = np.random.default_rng(42); x = rng.normal(size=100)
    return pd.DataFrame({"x": x, "category": np.where(x > 0, "a", "b"), "target": 3 * x + rng.normal(0, .1, 100), "label": (x > 0).astype(int)})


def test_regression_classification_clustering_and_anomaly(tmp_path):
    frame = data()
    regression, _ = run_ml(frame, {"task": "regression", "target": "target", "features": ["x", "category"], "random_seed": 42}, tmp_path / "r")
    classification, _ = run_ml(frame, {"task": "binary_classification", "target": "label", "features": ["x", "category"], "random_seed": 42}, tmp_path / "c")
    clustering, _ = run_ml(frame, {"task": "clustering", "features": ["x"], "random_seed": 42}, tmp_path / "k")
    anomaly, artifact = run_ml(frame, {"task": "anomaly_detection", "features": ["x"], "random_seed": 42}, tmp_path / "a")
    assert regression["metrics"]["r2"] > .9
    assert classification["metrics"]["accuracy"] > .9
    assert clustering["metrics"]["silhouette"] is not None
    assert len(anomaly["anomaly_scores"]) == len(frame) and artifact
