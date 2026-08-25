from datetime import datetime, timezone

import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.maintenance_causal import estimate_maintenance_effect, maintenance_counterfactual


def _causal_records(count: int = 400):
    rng = np.random.default_rng(17)
    load = rng.normal(size=count)
    treatment = (load + rng.normal(size=count) > 0).astype(int)
    change = -2.5 * treatment + 1.8 * load + rng.normal(0, 0.2, size=count)
    return [{"treatment_applied": bool(treatment[index]), "pre_outcome": 5.0, "post_outcome": 5.0 + float(change[index]), "covariates": {"load": float(load[index])}} for index in range(count)]


def test_maintenance_effect_recovers_intervention_and_abstains_without_adjustment():
    edges = [["load", "treatment_applied"], ["load", "outcome_change"], ["treatment_applied", "outcome_change"]]
    estimated = estimate_maintenance_effect(_causal_records(), confounders=["load"], dag_edges=edges)
    assert estimated["validity_status"] == "estimated_with_assumptions"
    assert abs(estimated["estimated_effect"] - -2.5) < 0.1

    abstained = estimate_maintenance_effect(_causal_records(), confounders=[], dag_edges=edges)
    assert abstained["validity_status"] == "abstained"
    assert abstained["abstention_reason"] == "unadjusted_common_causes"
    assert abstained["estimated_effect"] is None

    scenario = maintenance_counterfactual(estimated, current_outcome=5.7, apply_intervention=True, feasible=True, infeasibility_reason=None, lower_is_better=True)
    assert abs(scenario["estimated_outcome"] - 3.2) < 0.1
    assert scenario["estimated_benefit"] > 0


def test_maintenance_causal_api_persists_abstention():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        machine = client.post("/api/machines", json={"name": "Causal Motor"}).json()
        experiment = client.post(f"/api/machines/{machine['id']}/maintenance-experiments", json={
            "intervention": "correct_imbalance", "treatment_applied": True, "outcome_metric": "vibration_rms",
            "pre_outcome": 5.7, "post_outcome": 3.3, "covariates": {"load": 0.8}, "confirmed": True,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        assert experiment.status_code == 201
        study = client.post("/api/maintenance-causal-studies", json={
            "intervention": "correct_imbalance", "outcome_metric": "vibration_rms", "confounders": ["load"],
            "dag_edges": [["load", "treatment_applied"], ["load", "outcome_change"], ["treatment_applied", "outcome_change"]],
        })
        assert study.status_code == 201
        assert study.json()["status"] == "abstained"
        assert study.json()["estimated_effect"] is None
        scenario = client.post(f"/api/maintenance-causal-studies/{study.json()['id']}/counterfactuals", json={"machine_id": machine["id"], "current_outcome": 5.7})
        assert scenario.status_code == 201
        assert scenario.json()["status"] == "abstained"
        assert scenario.json()["result"]["estimated_outcome"] is None
    finally:
        app.dependency_overrides.clear()
