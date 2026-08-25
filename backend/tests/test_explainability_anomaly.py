from pathlib import Path

from app.services.anomaly_detection import score_anomaly, train_anomaly_model
from app.services.explainability import explain_fault_prediction
from app.services.fault_recognition import predict_fault, train_fault_models


def _training_evidence():
    rows = []
    labels = []
    for index in range(16):
        normal = index < 8
        rows.append({
            "rms": 0.5 + index * 0.002 if normal else 2.0 + index * 0.002,
            "dominant_frequency_hz": 20 + index * 0.1 if normal else 90 + index * 0.1,
            "crest_factor": 1.4 + index * 0.001 if normal else 2.8 + index * 0.001,
        })
        labels.append("normal" if normal else "imbalance")
    return rows, labels


def test_shap_explanation_is_linkable_and_additive(tmp_path: Path):
    rows, labels = _training_evidence()
    _, _, _, _, artifact = train_fault_models(rows, labels, artifact_dir=tmp_path / "fault", random_seed=42)
    predicted, _, _ = predict_fault(artifact, rows[-1])
    explanation = explain_fault_prediction(artifact, rows[-1], predicted, seed=42)
    assert explanation["method"] == "permutation_shap"
    assert set(explanation["contributions"]) == set(rows[-1])
    reconstructed = explanation["base_value"] + sum(explanation["contributions"].values())
    assert abs(reconstructed - explanation["output_value"]) < 0.000001


def test_isolation_forest_flags_unknown_without_fault_class(tmp_path: Path):
    rows, labels = _training_evidence()
    normal_rows = [row for row, label in zip(rows, labels) if label == "normal"]
    results, features, artifact = train_anomaly_model(normal_rows, artifact_dir=tmp_path / "anomaly", random_seed=42, contamination=0.05)
    normal_score, normal_anomaly = score_anomaly(artifact, normal_rows[3])
    unknown_score, unknown_anomaly = score_anomaly(artifact, {"rms": 20.0, "dominant_frequency_hz": 400.0, "crest_factor": 15.0})
    assert results["training_size"] == 8
    assert features == sorted(normal_rows[0])
    assert normal_anomaly is False
    assert unknown_anomaly is True
    assert unknown_score < normal_score
