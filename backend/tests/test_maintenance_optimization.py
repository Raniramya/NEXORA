from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.maintenance import (
    FaultPrediction, GeospatialAnalysisRun, Machine, MaintenanceCausalStudy,
    MaintenanceCounterfactual, SelectivePrediction, SignalWindow,
)
from app.services.maintenance_optimization import optimize_maintenance_schedule


def _candidates():
    return [
        {"candidate_id": "a", "machine_id": "m1", "risk": 0.9, "cost": 60, "downtime_hours": 2, "duration_hours": 2, "distance_km": 4, "causal_benefit": 5},
        {"candidate_id": "b", "machine_id": "m2", "risk": 0.7, "cost": 45, "downtime_hours": 1, "duration_hours": 1, "distance_km": 8, "causal_benefit": 3},
        {"candidate_id": "c", "machine_id": "m3", "risk": 0.4, "cost": 20, "downtime_hours": 3, "duration_hours": 2, "distance_km": 2, "causal_benefit": 2},
    ]


def test_nsga_ii_is_deterministic_feasible_and_compares_baselines() -> None:
    constraints = {"budget": 100, "max_downtime_hours": 4, "technician_hours": 4, "max_actions": 2}
    first = optimize_maintenance_schedule(_candidates(), constraints, population_size=30, generations=25, random_seed=7)
    second = optimize_maintenance_schedule(_candidates(), constraints, population_size=30, generations=25, random_seed=7)
    assert first == second
    assert first["status"] == "completed"
    assert set(first["baselines"]) == {"greedy_risk_cost", "conventional_risk_priority"}
    assert set(first["baseline_comparison"]) == set(first["baselines"])
    assert first["pareto_solutions"]
    for solution in first["pareto_solutions"]:
        objectives = solution["objectives"]
        assert objectives["cost"] <= constraints["budget"]
        assert objectives["downtime_hours"] <= constraints["max_downtime_hours"]
        assert solution["resource_usage"]["technician_hours"] <= constraints["technician_hours"]
        assert solution["resource_usage"]["action_count"] <= constraints["max_actions"]


def test_optimizer_abstains_without_eligible_candidates() -> None:
    result = optimize_maintenance_schedule([], {"budget": 1, "max_downtime_hours": 1, "technician_hours": 1, "max_actions": 1})
    assert result["status"] == "abstained"
    assert result["pareto_solutions"] == []


def test_optimization_api_gates_evidence_and_materializes_review_plan() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    machine = Machine(name="Motor A", asset_type="motor", status="active", latitude=12.97, longitude=77.59, metadata_json={})
    db.add(machine); db.flush()
    window = SignalWindow(machine_id=machine.id, recorded_at=datetime(2026, 8, 26, tzinfo=timezone.utc), sample_rate_hz=1000, channel="vibration", unit="g", samples=[0, 1], source="test", device_id=None, metadata_json={})
    db.add(window); db.flush()
    prediction = FaultPrediction(model_run_id="model", signal_window_id=window.id, predicted_class="bearing_fault", confidence=.9, probabilities={}, reliability_status="uncalibrated")
    db.add(prediction); db.flush()
    selective = SelectivePrediction(reliability_run_id="reliability", fault_prediction_id=prediction.id, anomaly_score_id=None, action="ACT", calibrated_probabilities={"normal": .1, "bearing_fault": .9}, prediction_set=["bearing_fault"], details={})
    db.add(selective)
    study = MaintenanceCausalStudy(intervention="replace_bearing", outcome_metric="vibration", status="estimated_with_assumptions", configuration={}, result={"estimated_effect": -2}, estimated_effect=-2)
    db.add(study); db.flush()
    counterfactual = MaintenanceCounterfactual(causal_study_id=study.id, machine_id=machine.id, configuration={}, result={"estimated_benefit": 2}, status="estimated_with_assumptions")
    db.add(counterfactual)
    distance = GeospatialAnalysisRun(analysis_type="haversine_distances", configuration={}, result={"distances": [{"machine_id": machine.id, "machine_name": machine.name, "distance_km": 3.5}]})
    db.add(distance); db.commit()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    payload = {
        "distance_analysis_run_id": distance.id,
        "candidates": [{"candidate_id": "bearing-a", "machine_id": machine.id, "selective_prediction_id": selective.id, "counterfactual_id": counterfactual.id, "action_type": "replace_bearing", "cost": 100, "downtime_hours": 2, "duration_hours": 1}],
        "budget": 200, "max_downtime_hours": 4, "technician_hours": 4, "max_actions": 1, "population_size": 12, "generations": 8, "random_seed": 4,
    }
    try:
        response = client.post("/api/maintenance-optimization-runs", json=payload)
        assert response.status_code == 201
        run = response.json()
        assert run["status"] == "completed"
        assert run["results"]["eligible_candidates"][0]["risk"] == .9
        assert run["provenance"]["candidates"][0]["signal_window_id"] == window.id
        selected_index = next(index for index, solution in enumerate(run["results"]["pareto_solutions"]) if solution["selected_candidate_ids"])
        plan = client.post(f"/api/maintenance-optimization-runs/{run['id']}/plans", json={"solution_index": selected_index})
        assert plan.status_code == 201
        assert plan.json()["status"] == "review_required"
        assert "does not create or authorize" in plan.json()["provenance"]["warning"]

        selective.action = "ABSTAIN"
        db.add(selective); db.commit()
        abstained = client.post("/api/maintenance-optimization-runs", json=payload)
        assert abstained.status_code == 201
        assert abstained.json()["status"] == "abstained"
        assert abstained.json()["results"]["excluded_candidates"][0]["reasons"] == ["reliability_action_is_not_act"]
    finally:
        app.dependency_overrides.clear()
        db.close()
