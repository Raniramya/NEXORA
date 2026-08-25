from datetime import datetime, timezone
from math import pi, sin
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.fault_recognition import predict_fault, train_fault_models


def test_fault_training_is_reproducible_and_predictions_are_uncalibrated(tmp_path: Path):
    rows = []
    labels = []
    for index in range(12):
        normal = index < 6
        rows.append({"rms": 0.5 + index * 0.001 if normal else 2.0 + index * 0.001, "dominant_frequency_hz": 20 + index if normal else 90 + index})
        labels.append("normal" if normal else "imbalance")
    first = train_fault_models(rows, labels, artifact_dir=tmp_path / "first", random_seed=42)
    second = train_fault_models(rows, labels, artifact_dir=tmp_path / "second", random_seed=42)
    assert first[0] == second[0]
    assert first[1] == second[1]
    assert {"random_forest", "svm_rbf", "xgboost"} <= set(first[0]["models"])
    predicted, confidence, probabilities = predict_fault(first[4], rows[-1])
    assert predicted == "imbalance"
    assert confidence is not None
    assert abs(sum(probabilities.values()) - 1) < 0.000001


def test_label_train_and_predict_api_workflow(tmp_path: Path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    settings = get_settings()
    previous_storage = settings.storage_path
    previous_token = settings.edge_ingest_token
    settings.storage_path = str(tmp_path)
    settings.edge_ingest_token = None
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        machine = client.post("/api/machines", json={"name": "Training Motor"}).json()
        window_ids = []
        for index in range(16):
            fault_class = "normal" if index < 8 else "imbalance"
            frequency = 20 + index * 0.1 if fault_class == "normal" else 90 + index * 0.1
            amplitude = 0.5 if fault_class == "normal" else 2.0
            samples = [amplitude * sin(2 * pi * frequency * point / 1000) for point in range(256)]
            window = client.post(f"/api/machines/{machine['id']}/signal-windows", json={"recorded_at": datetime.now(timezone.utc).isoformat(), "sample_rate_hz": 1000, "samples": samples}).json()
            window_ids.append(window["id"])
            label = client.put(f"/api/signal-windows/{window['id']}/label", json={"fault_class": fault_class, "label_source": "controlled_experiment", "confirmed": True})
            assert label.status_code == 200

        trained = client.post("/api/fault-model-runs", json={"machine_id": machine["id"], "random_seed": 42})
        assert trained.status_code == 201
        run = trained.json()
        assert run["status"] == "completed"
        assert run["winning_model"] in {"random_forest", "svm_rbf", "xgboost"}
        assert run["results"]["train_size"] + run["results"]["validation_size"] + run["results"]["calibration_size"] == 16

        predicted = client.post(f"/api/fault-model-runs/{run['id']}/predictions", json={"signal_window_id": window_ids[-1]})
        assert predicted.status_code == 201
        assert predicted.json()["predicted_class"] == "imbalance"
        assert predicted.json()["reliability_status"] == "uncalibrated"

        explained = client.post(f"/api/fault-predictions/{predicted.json()['id']}/explanation")
        assert explained.status_code == 201
        assert explained.json()["method"] == "permutation_shap"
        reconstructed = explained.json()["base_value"] + sum(explained.json()["contributions"].values())
        assert abs(reconstructed - explained.json()["output_value"]) < 0.000001

        anomaly_run = client.post("/api/anomaly-model-runs", json={"machine_id": machine["id"], "random_seed": 42})
        assert anomaly_run.status_code == 201
        anomaly_score = client.post(f"/api/anomaly-model-runs/{anomaly_run.json()['id']}/scores", json={"signal_window_id": window_ids[-1]})
        assert anomaly_score.status_code == 201
        assert anomaly_score.json()["interpretation"] in {"unknown_condition", "within_learned_normal_envelope"}
        assert "predicted_class" not in anomaly_score.json()
    finally:
        settings.storage_path = previous_storage
        settings.edge_ingest_token = previous_token
        app.dependency_overrides.clear()
