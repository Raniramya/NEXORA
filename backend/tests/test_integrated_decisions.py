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
    FaultExplanation, FaultModelRun, FaultPrediction, FaultReliabilityRun, GeospatialAnalysisRun, Machine,
    MaintenanceCausalStudy, MaintenanceCounterfactual, MaintenanceOptimizationRun,
    MaintenancePlan, SelectivePrediction, SignalFeatureSet, SignalWindow,
)


def test_integrated_decision_graph_review_and_action_creation() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    machine = Machine(name="Motor A", asset_type="motor", status="active", latitude=12.97, longitude=77.59, metadata_json={})
    db.add(machine); db.flush()
    window = SignalWindow(machine_id=machine.id, recorded_at=datetime.now(timezone.utc), sample_rate_hz=1000, channel="vibration", unit="g", samples=[0, 1], source="test", device_id=None, metadata_json={})
    db.add(window); db.flush()
    features = SignalFeatureSet(signal_window_id=window.id, extractor_version="test-v1", features={"rms": 1.2}, configuration={})
    db.add(features)
    model = FaultModelRun(machine_id=machine.id, status="completed", configuration={}, results={}, feature_names=["rms"], class_names=["normal", "bearing_fault"], winning_model="rf", artifact_location="test.joblib")
    db.add(model); db.flush()
    prediction = FaultPrediction(model_run_id=model.id, signal_window_id=window.id, predicted_class="bearing_fault", confidence=.9, probabilities={"bearing_fault": .9}, reliability_status="uncalibrated")
    db.add(prediction); db.flush()
    explanation = FaultExplanation(prediction_id=prediction.id, method="permutation_shap", explained_class="bearing_fault", base_value=.4, output_value=.9, contributions={"rms": .5}, feature_values={"rms": 1.2}, configuration={})
    db.add(explanation)
    reliability = FaultReliabilityRun(fault_model_run_id=model.id, status="calibrated", configuration={}, results={}, artifact_location="reliability.joblib")
    db.add(reliability); db.flush()
    selective = SelectivePrediction(reliability_run_id=reliability.id, fault_prediction_id=prediction.id, anomaly_score_id=None, action="ACT", calibrated_probabilities={"normal": .1, "bearing_fault": .9}, prediction_set=["bearing_fault"], details={})
    db.add(selective)
    study = MaintenanceCausalStudy(intervention="replace_bearing", outcome_metric="vibration", status="estimated_with_assumptions", configuration={}, result={"estimated_effect": -2}, estimated_effect=-2)
    db.add(study); db.flush()
    counterfactual = MaintenanceCounterfactual(causal_study_id=study.id, machine_id=machine.id, configuration={}, result={"estimated_benefit": 2}, status="estimated_with_assumptions")
    db.add(counterfactual)
    distance = GeospatialAnalysisRun(analysis_type="haversine_distances", configuration={}, result={"distances": [{"machine_id": machine.id, "distance_km": 3.5}]})
    db.add(distance); db.flush()
    candidate_id = "candidate-a"
    candidate = {"candidate_id": candidate_id, "machine_id": machine.id, "action_type": "replace_bearing", "risk": .9, "causal_benefit": 2, "distance_km": 3.5, "cost": 100, "downtime_hours": 2, "duration_hours": 1}
    links = {"candidate_id": candidate_id, "machine_id": machine.id, "selective_prediction_id": selective.id, "fault_prediction_id": prediction.id, "signal_window_id": window.id, "counterfactual_id": counterfactual.id, "causal_study_id": study.id, "distance_analysis_run_id": distance.id}
    optimization = MaintenanceOptimizationRun(status="completed", configuration={}, results={"eligible_candidates": [candidate], "baseline_comparison": {"greedy_risk_cost": {"pareto_solutions_dominating_baseline": 0}}}, provenance={"distance_analysis_run_id": distance.id, "candidates": [links]})
    db.add(optimization); db.flush()
    solution = {"selected_candidate_ids": [candidate_id], "selected_machine_ids": [machine.id], "objectives": {"residual_risk": 0, "cost": 100, "downtime_hours": 2, "travel_km": 3.5, "negative_causal_benefit": -2}, "resource_usage": {"action_count": 1, "technician_hours": 1}}
    plan = MaintenancePlan(optimization_run_id=optimization.id, solution_index=0, status="review_required", solution=solution, provenance={})
    db.add(plan); db.commit()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        response = client.post("/api/decisions/integrated-maintenance", json={"maintenance_plan_id": plan.id, "question": "Should the selected maintenance plan proceed?"})
        assert response.status_code == 201
        decision = response.json()
        assert decision["reliability_status"] == "REVIEW"
        assert "replace bearing for Motor A" in decision["recommendation"]
        assert decision["ecds"] is None
        evidence = client.get(f"/api/decisions/{decision['id']}/evidence").json()
        assert evidence[0]["payload"]["calibrated_fault_risk"] == .9
        graph = client.get(f"/api/decisions/{decision['id']}/evidence-graph").json()
        assert not graph["missing_links"]
        assert any(edge["relation"] == "CALIBRATED_AS" for edge in graph["edges"])
        assert not any(edge["source"].startswith("selective_prediction") and edge["target"].startswith("causal_study") for edge in graph["edges"])
        investigator = client.post("/api/investigator", json={"question": "Why is this recommended?", "decision_id": decision["id"]})
        assert investigator.status_code == 200
        assert evidence[0]["id"] in investigator.json()["answer"]
        review = client.post(f"/api/decisions/{decision['id']}/reviews", json={"reviewer": "Faculty Reviewer", "outcome": "approved", "notes": "Evidence checked."})
        assert review.status_code == 201
        assert len(review.json()["created_action_ids"]) == 1
        refreshed = client.get(f"/api/decisions/{decision['id']}").json()
        assert refreshed["reliability_status"] == "RECOMMEND"
        actions = client.get(f"/api/machines/{machine.id}/maintenance-actions").json()
        assert actions[0]["status"] == "planned"
        assert actions[0]["predicted_benefit"] == 2
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_integrated_decision_abstains_for_empty_plan() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    run = MaintenanceOptimizationRun(status="completed", configuration={}, results={"eligible_candidates": []}, provenance={"candidates": []})
    db.add(run); db.flush()
    plan = MaintenancePlan(optimization_run_id=run.id, solution_index=0, status="review_required", solution={"selected_candidate_ids": [], "objectives": {}}, provenance={})
    db.add(plan); db.commit()
    from app.services.integrated_decisions import create_integrated_decision
    decision = create_integrated_decision(db, plan.id, "Proceed with this empty plan?")
    assert decision.reliability_status == "ABSTAIN"
    assert decision.recommendation is None
    assert "selected_plan_has_no_actions" in decision.abstention_reason
    db.close()
