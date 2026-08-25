from pathlib import Path

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.maintenance import FaultModelRun, FaultPrediction, Machine, SignalFeatureSet, SignalWindow

from app.services.fault_recognition import train_fault_models
from app.services.uncertainty import evaluate_selective_prediction, fit_reliability_model


def _evidence(count: int):
    rows, labels = [], []
    half = count // 2
    for index in range(count):
        normal = index < half
        jitter = (index % half) * 0.004
        rows.append({"rms": 0.5 + jitter if normal else 2.0 + jitter, "dominant_frequency_hz": 20 + jitter if normal else 90 + jitter, "crest_factor": 1.4 + jitter if normal else 2.8 + jitter})
        labels.append("normal" if normal else "imbalance")
    return rows, labels


def test_calibration_conformal_and_selective_ood_gate(tmp_path: Path):
    rows, labels = _evidence(80)
    _, _, _, _, fault_artifact = train_fault_models(rows, labels, artifact_dir=tmp_path / "fault", random_seed=42)
    status, results, reliability_artifact = fit_reliability_model(fault_artifact, artifact_dir=tmp_path / "reliability", alpha=0.1, minimum_calibration_size=20)
    assert status == "calibrated"
    assert reliability_artifact
    assert results["calibration_size"] == 20
    assert results["empirical_calibration_coverage"] >= 0.9
    assert "multiclass_brier" in results["raw_metrics"] and "expected_calibration_error" in results["calibrated_metrics"]

    accepted = evaluate_selective_prediction(reliability_artifact, rows[-1], anomaly_is_ood=False)
    assert abs(sum(accepted["calibrated_probabilities"].values()) - 1) < 0.000001
    assert accepted["action"] in {"ACT", "MONITOR", "ABSTAIN"}
    assert accepted["prediction_set"]

    rejected = evaluate_selective_prediction(reliability_artifact, rows[-1], anomaly_is_ood=True)
    assert rejected["action"] == "ABSTAIN"
    assert rejected["anomaly_is_ood"] is True


def test_reliability_abstains_without_independent_calibration_size(tmp_path: Path):
    rows, labels = _evidence(16)
    _, _, _, _, fault_artifact = train_fault_models(rows, labels, artifact_dir=tmp_path / "fault", random_seed=42)
    status, results, artifact = fit_reliability_model(fault_artifact, artifact_dir=tmp_path / "reliability", minimum_calibration_size=20)
    assert status == "abstained"
    assert results["abstention_reason"] == "insufficient_independent_calibration_evidence"
    assert artifact is None


def test_reliability_api_persists_low_evidence_abstention(tmp_path: Path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    rows, labels = _evidence(16)
    _, winner, features, classes, fault_artifact = train_fault_models(rows, labels, artifact_dir=tmp_path / "fault", random_seed=42)
    with session_factory() as db:
        machine = Machine(name="Reliability Motor")
        db.add(machine); db.flush()
        window = SignalWindow(machine_id=machine.id, recorded_at=datetime.now(timezone.utc), sample_rate_hz=1000, samples=[0.0] * 8, channel="vibration", unit="g", source="test", metadata_json={})
        db.add(window); db.flush()
        window.feature_set = SignalFeatureSet(extractor_version="test", features=rows[-1], configuration={})
        run = FaultModelRun(machine_id=machine.id, status="completed", configuration={}, results={}, feature_names=features, class_names=classes, winning_model=winner, artifact_location=fault_artifact)
        db.add(run); db.flush()
        prediction = FaultPrediction(model_run_id=run.id, signal_window_id=window.id, predicted_class="imbalance", confidence=0.9, probabilities={"imbalance": 0.9, "normal": 0.1}, reliability_status="uncalibrated")
        db.add(prediction); db.commit()
        run_id, prediction_id = run.id, prediction.id

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    settings = get_settings(); previous_storage = settings.storage_path; settings.storage_path = str(tmp_path)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        reliability = client.post("/api/fault-reliability-runs", json={"fault_model_run_id": run_id, "minimum_calibration_size": 20})
        assert reliability.status_code == 201
        assert reliability.json()["status"] == "abstained"
        evaluated = client.post(f"/api/fault-reliability-runs/{reliability.json()['id']}/evaluations", json={"fault_prediction_id": prediction_id})
        assert evaluated.status_code == 201
        assert evaluated.json()["action"] == "ABSTAIN"
        assert evaluated.json()["calibrated_probabilities"] == {}
    finally:
        settings.storage_path = previous_storage
        app.dependency_overrides.clear()
