from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.models.decision import Decision, DecisionEvidenceRecord, DecisionReview, IntegratedDecisionWorkflow, ProvenanceEdge, ProvenanceNode
from app.models.maintenance import (
    AnomalyScore, FaultExplanation, FaultModelRun, FaultPrediction, FaultReliabilityRun, GeospatialAnalysisRun, Machine,
    MaintenanceAction, MaintenanceCausalStudy, MaintenanceCounterfactual,
    MaintenanceOptimizationRun, MaintenancePlan, SelectivePrediction, SignalWindow,
)


def _resource(db, model, resource_id: str | None, missing: list[str], label: str):
    value = db.get(model, resource_id) if resource_id else None
    if value is None:
        missing.append(label)
    return value


def create_integrated_decision(db, plan_id: str, question: str) -> Decision:
    existing = db.query(IntegratedDecisionWorkflow).filter(IntegratedDecisionWorkflow.maintenance_plan_id == plan_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="This maintenance plan already has an integrated decision.")
    plan = db.get(MaintenancePlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Maintenance plan not found.")
    run = db.get(MaintenanceOptimizationRun, plan.optimization_run_id)
    if not run:
        raise HTTPException(status_code=422, detail="Optimization run provenance is missing.")

    selected_ids = plan.solution.get("selected_candidate_ids", [])
    candidates = {item["candidate_id"]: item for item in run.results.get("eligible_candidates", [])}
    provenance = {item["candidate_id"]: item for item in run.provenance.get("candidates", [])}
    missing: list[str] = []
    if plan.status != "review_required":
        missing.append("plan_not_awaiting_review")
    if not selected_ids:
        missing.append("selected_plan_has_no_actions")

    resources: list[dict[str, Any]] = []
    relations: list[tuple[str, str, str]] = []
    evidence_records = []
    recommendation_items = []
    for candidate_id in selected_ids:
        candidate, links = candidates.get(candidate_id), provenance.get(candidate_id)
        if not candidate or not links:
            missing.append(f"candidate_provenance_missing:{candidate_id}")
            continue
        machine = _resource(db, Machine, links.get("machine_id"), missing, f"machine_missing:{candidate_id}")
        window = _resource(db, SignalWindow, links.get("signal_window_id"), missing, f"signal_window_missing:{candidate_id}")
        prediction = _resource(db, FaultPrediction, links.get("fault_prediction_id"), missing, f"fault_prediction_missing:{candidate_id}")
        evaluation = _resource(db, SelectivePrediction, links.get("selective_prediction_id"), missing, f"selective_prediction_missing:{candidate_id}")
        reliability_run = _resource(db, FaultReliabilityRun, evaluation.reliability_run_id if evaluation else None, missing, f"reliability_run_missing:{candidate_id}")
        anomaly = db.get(AnomalyScore, evaluation.anomaly_score_id) if evaluation and evaluation.anomaly_score_id else None
        if evaluation and evaluation.anomaly_score_id and not anomaly:
            missing.append(f"anomaly_score_missing:{candidate_id}")
        counterfactual = _resource(db, MaintenanceCounterfactual, links.get("counterfactual_id"), missing, f"counterfactual_missing:{candidate_id}")
        study = _resource(db, MaintenanceCausalStudy, links.get("causal_study_id"), missing, f"causal_study_missing:{candidate_id}")
        explanation = db.query(FaultExplanation).filter(FaultExplanation.prediction_id == prediction.id).first() if prediction else None
        if not explanation:
            missing.append(f"fault_explanation_missing:{candidate_id}")
        model_run = _resource(db, FaultModelRun, prediction.model_run_id if prediction else None, missing, f"fault_model_run_missing:{candidate_id}")
        feature_set = window.feature_set if window else None
        if not feature_set:
            missing.append(f"feature_set_missing:{candidate_id}")
        if evaluation and evaluation.action != "ACT":
            missing.append(f"reliability_no_longer_act:{candidate_id}")
        if prediction and window and prediction.signal_window_id != window.id:
            missing.append(f"prediction_window_mismatch:{candidate_id}")
        if evaluation and prediction and evaluation.fault_prediction_id != prediction.id:
            missing.append(f"reliability_prediction_mismatch:{candidate_id}")
        if reliability_run and prediction and reliability_run.fault_model_run_id != prediction.model_run_id:
            missing.append(f"reliability_model_mismatch:{candidate_id}")
        if counterfactual and machine and counterfactual.machine_id != machine.id:
            missing.append(f"counterfactual_machine_mismatch:{candidate_id}")
        if counterfactual and (counterfactual.status != "estimated_with_assumptions" or float(counterfactual.result.get("estimated_benefit", 0)) <= 0):
            missing.append(f"causal_benefit_invalid:{candidate_id}")
        predictive_resources = [
            ("machine", machine), ("signal_window", window), ("feature_set", feature_set), ("fault_model_run", model_run),
            ("fault_prediction", prediction), ("fault_explanation", explanation), ("fault_reliability_run", reliability_run),
            ("anomaly_score", anomaly), ("selective_prediction", evaluation),
        ]
        for resource_type, resource in predictive_resources:
            if resource is None:
                continue
            key = f"{resource_type}:{resource.id}"
            resources.append({"key": key, "resource_type": resource_type, "resource_id": resource.id})
        if machine and window: relations.append((f"machine:{machine.id}", f"signal_window:{window.id}", "OBSERVED_AS"))
        if window and feature_set: relations.append((f"signal_window:{window.id}", f"feature_set:{feature_set.id}", "DERIVED_FEATURES"))
        if feature_set and prediction: relations.append((f"feature_set:{feature_set.id}", f"fault_prediction:{prediction.id}", "INPUT_TO"))
        if model_run and prediction: relations.append((f"fault_model_run:{model_run.id}", f"fault_prediction:{prediction.id}", "MODEL_FOR"))
        if prediction and explanation: relations.append((f"fault_prediction:{prediction.id}", f"fault_explanation:{explanation.id}", "EXPLAINED_BY"))
        if prediction and evaluation: relations.append((f"fault_prediction:{prediction.id}", f"selective_prediction:{evaluation.id}", "CALIBRATED_AS"))
        if reliability_run and evaluation: relations.append((f"fault_reliability_run:{reliability_run.id}", f"selective_prediction:{evaluation.id}", "CALIBRATION_MODEL_FOR"))
        if anomaly and evaluation: relations.append((f"anomaly_score:{anomaly.id}", f"selective_prediction:{evaluation.id}", "OOD_GATE_FOR"))
        candidate_key = f"candidate:{candidate_id}"
        resources.append({"key": candidate_key, "resource_type": "optimization_candidate", "resource_id": candidate_id})
        if evaluation:
            relations.append((f"selective_prediction:{evaluation.id}", candidate_key, "SUPPORTS"))
        causal_prior = None
        for resource_type, resource in (("causal_study", study), ("counterfactual", counterfactual)):
            if resource is None:
                continue
            key = f"{resource_type}:{resource.id}"
            resources.append({"key": key, "resource_type": resource_type, "resource_id": resource.id})
            if causal_prior:
                relations.append((causal_prior, key, "ESTIMATES"))
            causal_prior = key
        if causal_prior:
            relations.append((causal_prior, candidate_key, "SUPPORTS"))
        evidence_records.append({
            "evidence_type": "integrated_maintenance_candidate", "source_type": "optimization_candidate", "source_id": None,
            "payload": {
                "candidate_id": candidate_id, "machine_id": candidate["machine_id"], "action_type": candidate["action_type"],
                "calibrated_fault_risk": candidate["risk"], "identified_causal_benefit": candidate["causal_benefit"],
                "haversine_distance_km": candidate["distance_km"], "declared_cost": candidate["cost"],
                "declared_downtime_hours": candidate["downtime_hours"], "declared_duration_hours": candidate["duration_hours"],
            },
            "uncertainty": {"selective_action": evaluation.action if evaluation else None, "counterfactual_status": counterfactual.status if counterfactual else None},
            "metadata_json": links,
        })
        if machine:
            recommendation_items.append(f"{candidate['action_type'].replace('_', ' ')} for {machine.name}")

    distance_id = run.provenance.get("distance_analysis_run_id")
    distance_run = _resource(db, GeospatialAnalysisRun, distance_id, missing, "distance_run_missing")
    distance_machine_ids = {item.get("machine_id") for item in distance_run.result.get("distances", [])} if distance_run else set()
    for candidate_id in selected_ids:
        candidate = candidates.get(candidate_id)
        if candidate and candidate["machine_id"] not in distance_machine_ids:
            missing.append(f"distance_machine_missing:{candidate_id}")
    shared = [("distance_analysis", distance_run), ("optimization_run", run), ("maintenance_plan", plan)]
    for resource_type, resource in shared:
        if resource:
            resources.append({"key": f"{resource_type}:{resource.id}", "resource_type": resource_type, "resource_id": resource.id})
    for candidate_id in selected_ids:
        if candidate_id in candidates:
            relations.append((f"candidate:{candidate_id}", f"optimization_run:{run.id}", "OPTIMIZED_IN"))
    if distance_run:
        relations.append((f"distance_analysis:{distance_run.id}", f"optimization_run:{run.id}", "USED_IN"))
    relations.append((f"optimization_run:{run.id}", f"maintenance_plan:{plan.id}", "SELECTED_AS"))

    status = "ABSTAIN" if missing else "REVIEW"
    recommendation = None if missing else "Human review requested for: " + "; ".join(recommendation_items) + "."
    decision = Decision(
        question=question, decision_type="integrated_maintenance", recommendation=recommendation,
        reliability_status=status, ecds=None, review_required=status == "REVIEW",
        abstention_reason="; ".join(missing) or None,
        reliability_details={
            "gate": "complete_integrated_evidence_chain", "missing_links": missing,
            "selected_solution_objectives": plan.solution.get("objectives", {}),
            "baseline_comparison": run.results.get("baseline_comparison", {}),
            "warning": "Recommendation is plan-derived and requires named human review before maintenance actions are created.",
        },
    )
    db.add(decision); db.flush()
    root = ProvenanceNode(node_type="decision", resource_type="decision", resource_id=decision.id, metadata_json={"status": status, "workflow": "integrated_maintenance"})
    db.add(root); db.flush(); decision.provenance_root_id = root.id
    unique_resources = {item["key"]: item for item in resources}
    node_ids = {}
    for key, item in unique_resources.items():
        node = ProvenanceNode(node_type="evidence", resource_type=item["resource_type"], resource_id=item["resource_id"], metadata_json={})
        db.add(node); db.flush(); node_ids[key] = node.id
    graph_edges = []
    for source, target, relation in relations:
        if source in node_ids and target in node_ids:
            db.add(ProvenanceEdge(source_node_id=node_ids[source], target_node_id=node_ids[target], relation_type=relation))
            graph_edges.append({"source": source, "target": target, "relation": relation})
    plan_key = f"maintenance_plan:{plan.id}"
    if plan_key in node_ids:
        db.add(ProvenanceEdge(source_node_id=node_ids[plan_key], target_node_id=root.id, relation_type="SUPPORTS_DECISION"))
        graph_edges.append({"source": plan_key, "target": f"decision:{decision.id}", "relation": "SUPPORTS_DECISION"})
    for item in evidence_records:
        record = DecisionEvidenceRecord(**item); db.add(record); decision.evidence.append(record)
    graph = {"nodes": list(unique_resources.values()) + [{"key": f"decision:{decision.id}", "resource_type": "decision", "resource_id": decision.id}], "edges": graph_edges, "missing_links": missing}
    db.add(IntegratedDecisionWorkflow(decision_id=decision.id, maintenance_plan_id=plan.id, readiness_status=status, evidence_graph=graph))
    db.commit(); db.refresh(decision)
    return decision


def review_integrated_decision(db, decision_id: str, reviewer: str, outcome: str, notes: str | None) -> DecisionReview:
    decision = db.get(Decision, decision_id)
    workflow = db.query(IntegratedDecisionWorkflow).filter(IntegratedDecisionWorkflow.decision_id == decision_id).first()
    if not decision or not workflow:
        raise HTTPException(status_code=404, detail="Integrated decision not found.")
    if db.query(DecisionReview).filter(DecisionReview.decision_id == decision_id).first():
        raise HTTPException(status_code=409, detail="This decision has already been reviewed.")
    if decision.reliability_status != "REVIEW":
        raise HTTPException(status_code=422, detail="Only evidence-complete REVIEW decisions can be reviewed.")
    action_ids = []
    if outcome == "approved":
        plan = db.get(MaintenancePlan, workflow.maintenance_plan_id)
        run = db.get(MaintenanceOptimizationRun, plan.optimization_run_id)
        candidates = {item["candidate_id"]: item for item in run.results.get("eligible_candidates", [])}
        for candidate_id in plan.solution.get("selected_candidate_ids", []):
            candidate = candidates[candidate_id]
            action = MaintenanceAction(
                machine_id=candidate["machine_id"], action_type=candidate["action_type"], status="planned",
                predicted_benefit=candidate["causal_benefit"], notes=f"Created from approved integrated decision {decision.id}; observed benefit remains pending.",
            )
            db.add(action); db.flush(); action_ids.append(action.id)
        decision.reliability_status = "RECOMMEND"
        decision.review_required = False
    else:
        decision.reliability_status = "ABSTAIN"
        decision.review_required = False
        decision.abstention_reason = "Rejected by named human reviewer."
        decision.recommendation = None
    review = DecisionReview(decision_id=decision.id, reviewer=reviewer, outcome=outcome, notes=notes, created_action_ids=action_ids)
    db.add(review); db.commit(); db.refresh(review)
    return review
