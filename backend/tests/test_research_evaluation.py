from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.routes as routes_module
import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.maintenance import Machine, MaintenanceAction, SensorReading
from app.models.research import BenchmarkObservation
from app.services.research_evaluation import evaluate_benchmark, physical_trial_result, summarize_physical_trials, write_reproducible_report


def _benchmark_rows():
    rows = []
    outputs = {
        "integrated": [(True, "repair", False, True, ["decision-1"]), (False, None, False, True, ["decision-2"]), (True, "inspect", False, True, ["decision-3"])],
        "traditional_analytics": [(True, "repair", False, False, ["chart-1"]), (True, "repair", True, False, ["chart-2"]), (True, "inspect", False, False, ["chart-3"])],
        "predictive_ml_only": [(True, "repair", False, False, ["prediction-1"]), (True, "inspect", False, False, ["prediction-2"]), (True, "repair", True, False, ["prediction-3"])],
        "llm_only": [(True, "inspect", True, False, []), (True, "repair", True, False, []), (True, "repair", True, False, [])],
        "integrated_no_causal": [(True, "repair", False, True, ["prediction-1"]), (True, "inspect", False, True, ["prediction-2"]), (True, "repair", False, True, ["prediction-3"])],
    }
    truth = ["repair", "inspect", "inspect"]
    for variant, variant_outputs in outputs.items():
        for index, (made, action, harm, uncertainty, provenance) in enumerate(variant_outputs):
            rows.append({"case_id": f"case-{index}", "system_variant": variant, "recommendation_made": made, "predicted_action": action, "ground_truth_action": truth[index], "observed_harm": harm, "uncertainty_handled": uncertainty, "provenance_references": provenance})
    return rows


def test_physical_metrics_and_report_are_computed_and_reproducible(tmp_path: Path) -> None:
    result = physical_trial_result(pre_value=5.7, post_value=3.3, predicted_benefit=2.6, lower_is_better=True)
    assert abs(result["observed_benefit"] - 2.4) < 1e-12
    assert abs(result["absolute_error"] - .2) < 1e-12
    summary = summarize_physical_trials([
        {"predicted_benefit": 2.6, "observed_benefit": 2.4},
        {"predicted_benefit": 2.0, "observed_benefit": 2.1},
        {"predicted_benefit": 1.5, "observed_benefit": 1.5},
    ], minimum_trials=3)
    assert summary["status"] == "completed"
    assert abs(summary["mean_absolute_error"] - .1) < 1e-12
    first = write_reproducible_report(tmp_path, "run", {"results": summary})
    second = write_reproducible_report(tmp_path, "run", {"results": summary})
    assert first[1] == second[1]
    assert len(first[1]) == 64


def test_benchmark_requires_aligned_baselines_and_computes_ablations() -> None:
    incomplete = evaluate_benchmark([row for row in _benchmark_rows() if row["system_variant"] != "llm_only"], 3)
    assert incomplete["status"] == "abstained"
    assert incomplete["missing_required_variants"] == ["llm_only"]
    result = evaluate_benchmark(_benchmark_rows(), 3)
    assert result["status"] == "completed"
    assert result["variant_metrics"]["integrated"]["coverage"] == 2 / 3
    assert result["variant_metrics"]["integrated"]["selective_accuracy"] == 1
    assert result["variant_metrics"]["llm_only"]["provenance_coverage"] == 0
    assert "integrated_no_causal" in result["integrated_minus_variant"]


def test_research_api_links_physical_readings_and_persists_benchmark_report(tmp_path: Path) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    machine = Machine(name="Motor", asset_type="motor", status="active", metadata_json={})
    db.add(machine); db.flush()
    action = MaintenanceAction(machine_id=machine.id, action_type="correct_imbalance", status="planned", predicted_benefit=2.6)
    db.add(action); db.flush()
    now = datetime.now(timezone.utc)
    pre = SensorReading(machine_id=machine.id, recorded_at=now, vibration_rms=5.7, temperature=None, current=None, rpm=None, features={})
    post = SensorReading(machine_id=machine.id, recorded_at=now + timedelta(hours=1), vibration_rms=3.3, temperature=None, current=None, rpm=None, features={})
    db.add_all([pre, post])
    for row in _benchmark_rows():
        db.add(BenchmarkObservation(benchmark_name="paper-v1", evidence_source="recorded faculty-adjudicated case", metadata_json={}, **row))
    db.commit()

    def override_get_db():
        session = session_factory()
        try: yield session
        finally: session.close()

    original_settings = routes_module.get_settings
    routes_module.get_settings = lambda: SimpleNamespace(storage_path=str(tmp_path))
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        trial = client.post("/api/research/physical-trials", json={"maintenance_action_id": action.id, "pre_reading_id": pre.id, "post_reading_id": post.id, "outcome_metric": "vibration_rms", "lower_is_better": True, "confirmed": True})
        assert trial.status_code == 201
        assert abs(trial.json()["observed_benefit"] - 2.4) < 1e-12
        invalid = client.post("/api/research/physical-trials", json={"maintenance_action_id": action.id, "pre_reading_id": post.id, "post_reading_id": pre.id, "outcome_metric": "vibration_rms", "lower_is_better": True, "confirmed": True})
        assert invalid.status_code == 422
        evaluation = client.post("/api/research/evaluations/benchmark", json={"benchmark_name": "paper-v1", "minimum_aligned_cases": 3})
        assert evaluation.status_code == 201
        payload = evaluation.json()
        assert payload["status"] == "completed"
        assert Path(payload["artifact_location"]).exists()
        assert len(payload["artifact_sha256"]) == 64
    finally:
        routes_module.get_settings = original_settings
        app.dependency_overrides.clear()
        db.close()
