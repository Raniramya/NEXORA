from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
import secrets
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.ml_run import MLRun
from app.schemas.datasets import AnalyticsRequest, CleanedDatasetRequest, DatasetDetail, DatasetSummary, PreviewResponse
from app.schemas.ml import MLRunRequest, MLRunResponse
from app.services.analytics import aggregate, apply_filters, time_trend
from app.services.datasets import cleaned_copy, read_dataset
from app.services.profiling import profile_dataframe
from app.services.storage import LocalDatasetStorage
from app.services.ml_engine import run_ml
from app.models.decision import Decision,DecisionEvidenceRecord,ProvenanceNode,ProvenanceEdge
from app.models.causal_run import CausalAnalysis, ScenarioRun, ReliabilityEvaluation
from app.schemas.decisions import DecisionRequest
from app.schemas.decisions import DecisionReviewCreate, DecisionReviewResponse, IntegratedDecisionCreate
from app.services.decisions import create_decision
from app.services.integrated_decisions import create_integrated_decision, review_integrated_decision
from app.schemas.investigator import InvestigatorRequest
from app.services.investigator import investigate
from app.services.causal import estimate_effect, intervention_scenario
from app.schemas.causal import CausalRequest, ScenarioRequest
from app.models.maintenance import Machine, SensorReading, FaultEvent, MaintenanceAction, SignalFeatureSet, SignalWindow, SignalFaultLabel, FaultModelRun, FaultPrediction, FaultExplanation, AnomalyModelRun, AnomalyScore, MaintenanceExperiment, MaintenanceCausalStudy, MaintenanceCounterfactual, FaultReliabilityRun, SelectivePrediction
from app.schemas.maintenance import MachineCreate, MachineResponse, SensorReadingCreate, SensorReadingResponse, FaultEventCreate, FaultEventResponse, MaintenanceActionCreate, MaintenanceActionResponse, SignalWindowCreate, SignalWindowResponse, SignalFaultLabelCreate, SignalFaultLabelResponse, FaultModelRunCreate, FaultModelRunResponse, FaultPredictionCreate, FaultPredictionResponse, FaultExplanationResponse, AnomalyModelRunCreate, AnomalyModelRunResponse, AnomalyScoreCreate, AnomalyScoreResponse, MaintenanceExperimentCreate, MaintenanceExperimentResponse, MaintenanceCausalStudyCreate, MaintenanceCausalStudyResponse, MaintenanceCounterfactualCreate, MaintenanceCounterfactualResponse, FaultReliabilityRunCreate, FaultReliabilityRunResponse, SelectivePredictionCreate, SelectivePredictionResponse
from app.services.signal_processing import extract_signal_features
from app.services.fault_recognition import predict_fault, train_fault_models
from app.services.explainability import explain_fault_prediction
from app.services.anomaly_detection import score_anomaly, train_anomaly_model
from app.services.maintenance_causal import estimate_maintenance_effect, maintenance_counterfactual
from app.services.uncertainty import evaluate_selective_prediction, fit_reliability_model
from app.models.maintenance import GeospatialAnalysisRun
from app.schemas.maintenance import AssetMapItem, DistanceRequest, GeospatialAnalysisRunResponse, HotspotAnalysisCreate
from app.services.geospatial import EARTH_RADIUS_KM, asset_distances, cluster_fault_hotspots
from app.models.maintenance import MaintenanceOptimizationRun, MaintenancePlan
from app.schemas.maintenance import MaintenanceOptimizationCreate, MaintenanceOptimizationRunResponse, MaintenancePlanCreate, MaintenancePlanResponse
from app.services.maintenance_optimization import optimize_maintenance_schedule
from app.models.decision import DecisionReview, IntegratedDecisionWorkflow
from app.models.research import BenchmarkObservation, PhysicalValidationTrial, ResearchEvaluationRun
from app.schemas.research import BenchmarkEvaluationCreate, BenchmarkObservationCreate, BenchmarkObservationResponse, PhysicalEvaluationCreate, PhysicalValidationTrialCreate, PhysicalValidationTrialResponse, ResearchEvaluationRunResponse
from app.services.research_evaluation import evaluate_benchmark, physical_trial_result, summarize_physical_trials, write_reproducible_report
from app.models.maintenance import EdgeIngestionReceipt
from app.schemas.maintenance import EdgeSignalEnvelope
from pathlib import Path

router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", tags=["system"])
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.post("/machines", response_model=MachineResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance"])
def create_machine(request: MachineCreate, db: Session = Depends(get_db)) -> Machine:
    machine = Machine(**request.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


@router.get("/machines", response_model=list[MachineResponse], tags=["maintenance"])
def list_machines(db: Session = Depends(get_db)) -> list[Machine]:
    return db.query(Machine).order_by(Machine.created_at.desc()).all()


@router.get("/geo/assets", response_model=list[AssetMapItem], tags=["geospatial"])
def geospatial_assets(db: Session = Depends(get_db)) -> list[dict]:
    assets = db.query(Machine).filter(Machine.latitude.is_not(None), Machine.longitude.is_not(None)).order_by(Machine.name).all()
    rows = []
    for asset in assets:
        faults = db.query(FaultEvent).filter(FaultEvent.machine_id == asset.id).order_by(FaultEvent.observed_at.desc()).all()
        rows.append({
            "machine_id": asset.id,
            "machine_name": asset.name,
            "status": asset.status,
            "latitude": asset.latitude,
            "longitude": asset.longitude,
            "fault_event_count": len(faults),
            "latest_fault_type": faults[0].fault_type if faults else None,
        })
    return rows


@router.post("/geo/distances", response_model=GeospatialAnalysisRunResponse, status_code=status.HTTP_201_CREATED, tags=["geospatial"])
def calculate_asset_distances(request: DistanceRequest, db: Session = Depends(get_db)) -> GeospatialAnalysisRun:
    assets = db.query(Machine).all()
    distances = asset_distances(request.origin_latitude, request.origin_longitude, [{
        "machine_id": asset.id, "machine_name": asset.name,
        "latitude": asset.latitude, "longitude": asset.longitude,
    } for asset in assets])
    run = GeospatialAnalysisRun(
        analysis_type="haversine_distances",
        configuration=request.model_dump(),
        result={
            "distances": distances,
            "included_asset_count": len(distances),
            "excluded_asset_count": len(assets) - len(distances),
            "method": "haversine_great_circle",
            "earth_radius_km": EARTH_RADIUS_KM,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.post("/geo/hotspots", response_model=GeospatialAnalysisRunResponse, status_code=status.HTTP_201_CREATED, tags=["geospatial"])
def create_hotspot_analysis(request: HotspotAnalysisCreate, db: Session = Depends(get_db)) -> GeospatialAnalysisRun:
    cutoff = datetime.now(timezone.utc) - timedelta(days=request.lookback_days)
    faults = db.query(FaultEvent).filter(FaultEvent.observed_at >= cutoff).all()
    machines = {machine.id: machine for machine in db.query(Machine).all()}
    events = []
    for fault in faults:
        machine = machines.get(fault.machine_id)
        if machine is None:
            continue
        events.append({
            "event_id": fault.id, "machine_id": machine.id, "machine_name": machine.name,
            "latitude": machine.latitude, "longitude": machine.longitude,
        })
    result = cluster_fault_hotspots(events, epsilon_km=request.epsilon_km, minimum_assets=request.minimum_assets)
    configuration = {**request.model_dump(), "cutoff_utc": cutoff.isoformat()}
    run = GeospatialAnalysisRun(analysis_type="dbscan_fault_hotspots", configuration=configuration, result=result)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/maintenance-optimization/evidence", tags=["maintenance-optimization"])
def maintenance_optimization_evidence(db: Session = Depends(get_db)) -> dict:
    distance_run = db.query(GeospatialAnalysisRun).filter(GeospatialAnalysisRun.analysis_type == "haversine_distances").order_by(GeospatialAnalysisRun.created_at.desc()).first()
    distances = {item["machine_id"]: float(item["distance_km"]) for item in (distance_run.result.get("distances", []) if distance_run else [])}
    rows = []
    for machine in db.query(Machine).order_by(Machine.name).all():
        evaluation = None
        for item in db.query(SelectivePrediction).order_by(SelectivePrediction.created_at.desc()).all():
            prediction = db.get(FaultPrediction, item.fault_prediction_id)
            window = db.get(SignalWindow, prediction.signal_window_id) if prediction else None
            if window and window.machine_id == machine.id:
                evaluation = item
                break
        counterfactual = db.query(MaintenanceCounterfactual).filter(
            MaintenanceCounterfactual.machine_id == machine.id,
            MaintenanceCounterfactual.status == "estimated_with_assumptions",
        ).order_by(MaintenanceCounterfactual.created_at.desc()).first()
        study = db.get(MaintenanceCausalStudy, counterfactual.causal_study_id) if counterfactual else None
        missing = []
        if not evaluation or evaluation.action != "ACT":
            missing.append("ACT reliability evaluation")
        if not counterfactual or counterfactual.result.get("estimated_benefit") is None or float(counterfactual.result["estimated_benefit"]) <= 0:
            missing.append("positive identified causal counterfactual")
        if machine.id not in distances:
            missing.append("Haversine distance")
        probabilities = evaluation.calibrated_probabilities if evaluation else {}
        fault_probabilities = [float(value) for name, value in probabilities.items() if name.lower() != "normal"]
        rows.append({
            "machine_id": machine.id, "machine_name": machine.name, "eligible": not missing, "missing_evidence": missing,
            "selective_prediction_id": evaluation.id if evaluation else None,
            "counterfactual_id": counterfactual.id if counterfactual else None,
            "action_type": study.intervention if study else None,
            "calibrated_fault_risk": max(fault_probabilities, default=None),
            "causal_benefit": counterfactual.result.get("estimated_benefit") if counterfactual else None,
            "distance_km": distances.get(machine.id),
        })
    return {"distance_analysis_run_id": distance_run.id if distance_run else None, "candidates": rows}


@router.post("/maintenance-optimization-runs", response_model=MaintenanceOptimizationRunResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance-optimization"])
def create_maintenance_optimization_run(request: MaintenanceOptimizationCreate, db: Session = Depends(get_db)) -> MaintenanceOptimizationRun:
    distance_run = db.get(GeospatialAnalysisRun, request.distance_analysis_run_id)
    if not distance_run or distance_run.analysis_type != "haversine_distances":
        raise HTTPException(status_code=422, detail="A persisted Haversine distance run is required.")
    distances = {item["machine_id"]: float(item["distance_km"]) for item in distance_run.result.get("distances", [])}
    eligible, exclusions, candidate_provenance = [], [], []
    for candidate_request in request.candidates:
        candidate = candidate_request.model_dump()
        machine = db.get(Machine, candidate["machine_id"])
        evaluation = db.get(SelectivePrediction, candidate["selective_prediction_id"])
        counterfactual = db.get(MaintenanceCounterfactual, candidate["counterfactual_id"])
        reasons = []
        prediction = db.get(FaultPrediction, evaluation.fault_prediction_id) if evaluation else None
        window = db.get(SignalWindow, prediction.signal_window_id) if prediction else None
        if not machine:
            reasons.append("machine_not_found")
        if not evaluation or evaluation.action != "ACT":
            reasons.append("reliability_action_is_not_act")
        if window and window.machine_id != candidate["machine_id"]:
            reasons.append("selective_prediction_machine_mismatch")
        if not counterfactual or counterfactual.machine_id != candidate["machine_id"]:
            reasons.append("counterfactual_machine_mismatch")
        elif counterfactual.status != "estimated_with_assumptions" or counterfactual.result.get("estimated_benefit") is None:
            reasons.append("causal_counterfactual_not_identified")
        elif float(counterfactual.result["estimated_benefit"]) <= 0:
            reasons.append("causal_benefit_is_not_positive")
        if candidate["machine_id"] not in distances:
            reasons.append("distance_evidence_missing")
        probabilities = evaluation.calibrated_probabilities if evaluation else {}
        fault_probabilities = {name: float(value) for name, value in probabilities.items() if name.lower() != "normal"}
        risk = max(fault_probabilities.values(), default=0.0)
        if evaluation and (not fault_probabilities or risk <= 0):
            reasons.append("no_calibrated_fault_risk")
        provenance = {
            "candidate_id": candidate["candidate_id"], "machine_id": candidate["machine_id"],
            "selective_prediction_id": candidate["selective_prediction_id"], "fault_prediction_id": prediction.id if prediction else None,
            "signal_window_id": window.id if window else None, "counterfactual_id": candidate["counterfactual_id"],
            "causal_study_id": counterfactual.causal_study_id if counterfactual else None,
            "distance_analysis_run_id": distance_run.id,
        }
        candidate_provenance.append(provenance)
        if reasons:
            exclusions.append({"candidate_id": candidate["candidate_id"], "reasons": reasons, "provenance": provenance})
            continue
        eligible.append({
            **candidate, "risk": risk, "causal_benefit": float(counterfactual.result["estimated_benefit"]),
            "distance_km": distances[candidate["machine_id"]],
        })
    constraints = {
        "budget": request.budget, "max_downtime_hours": request.max_downtime_hours,
        "technician_hours": request.technician_hours, "max_actions": request.max_actions,
    }
    results = optimize_maintenance_schedule(eligible, constraints, population_size=request.population_size, generations=request.generations, random_seed=request.random_seed)
    results["excluded_candidates"] = exclusions
    results["eligible_candidates"] = eligible
    run = MaintenanceOptimizationRun(
        status=results["status"], configuration=request.model_dump(), results=results,
        provenance={"distance_analysis_run_id": distance_run.id, "candidates": candidate_provenance},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/maintenance-optimization-runs", response_model=list[MaintenanceOptimizationRunResponse], tags=["maintenance-optimization"])
def list_maintenance_optimization_runs(db: Session = Depends(get_db)) -> list[MaintenanceOptimizationRun]:
    return db.query(MaintenanceOptimizationRun).order_by(MaintenanceOptimizationRun.created_at.desc()).all()


@router.post("/maintenance-optimization-runs/{run_id}/plans", response_model=MaintenancePlanResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance-optimization"])
def create_maintenance_plan(run_id: str, request: MaintenancePlanCreate, db: Session = Depends(get_db)) -> MaintenancePlan:
    run = db.get(MaintenanceOptimizationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Maintenance optimization run not found.")
    solutions = run.results.get("pareto_solutions", [])
    if run.status != "completed" or request.solution_index >= len(solutions):
        raise HTTPException(status_code=422, detail="A valid completed Pareto solution is required.")
    solution = solutions[request.solution_index]
    plan = MaintenancePlan(
        optimization_run_id=run.id, solution_index=request.solution_index, status="review_required", solution=solution,
        provenance={"optimization_run_id": run.id, "candidate_evidence": run.provenance.get("candidates", []), "warning": "Plan selection requires human review and does not create or authorize maintenance actions."},
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/maintenance-plans", response_model=list[MaintenancePlanResponse], tags=["maintenance-optimization"])
def list_maintenance_plans(db: Session = Depends(get_db)) -> list[MaintenancePlan]:
    return db.query(MaintenancePlan).order_by(MaintenancePlan.created_at.desc()).all()


@router.post("/research/physical-trials", response_model=PhysicalValidationTrialResponse, status_code=status.HTTP_201_CREATED, tags=["research-evaluation"])
def create_physical_validation_trial(request: PhysicalValidationTrialCreate, db: Session = Depends(get_db)) -> PhysicalValidationTrial:
    if not request.confirmed:
        raise HTTPException(status_code=422, detail="Only confirmed physical interventions can enter validation.")
    action = db.get(MaintenanceAction, request.maintenance_action_id)
    if not action or action.predicted_benefit is None:
        raise HTTPException(status_code=422, detail="A maintenance action with persisted predicted benefit is required.")
    pre, post = db.get(SensorReading, request.pre_reading_id), db.get(SensorReading, request.post_reading_id)
    if not pre or not post or pre.machine_id != action.machine_id or post.machine_id != action.machine_id:
        raise HTTPException(status_code=422, detail="Pre/post readings must belong to the maintenance-action machine.")
    if post.recorded_at <= pre.recorded_at:
        raise HTTPException(status_code=422, detail="Post-intervention reading must occur after the pre-intervention reading.")
    pre_value, post_value = getattr(pre, request.outcome_metric), getattr(post, request.outcome_metric)
    if pre_value is None or post_value is None:
        raise HTTPException(status_code=422, detail="Both readings must contain the selected measured outcome.")
    duplicate = db.query(PhysicalValidationTrial).filter(
        PhysicalValidationTrial.maintenance_action_id == action.id,
        PhysicalValidationTrial.pre_reading_id == pre.id,
        PhysicalValidationTrial.post_reading_id == post.id,
        PhysicalValidationTrial.outcome_metric == request.outcome_metric,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This physical validation comparison is already recorded.")
    result = physical_trial_result(pre_value=pre_value, post_value=post_value, predicted_benefit=action.predicted_benefit, lower_is_better=request.lower_is_better)
    trial = PhysicalValidationTrial(
        maintenance_action_id=action.id, pre_reading_id=pre.id, post_reading_id=post.id,
        outcome_metric=request.outcome_metric, predicted_benefit=action.predicted_benefit,
        observed_benefit=result["observed_benefit"], absolute_error=result["absolute_error"], result=result, confirmed=True,
    )
    action.observed_benefit = result["observed_benefit"]
    action.status = "completed"
    action.completed_at = post.recorded_at
    db.add(trial); db.commit(); db.refresh(trial)
    return trial


@router.get("/research/physical-trials", response_model=list[PhysicalValidationTrialResponse], tags=["research-evaluation"])
def list_physical_validation_trials(db: Session = Depends(get_db)) -> list[PhysicalValidationTrial]:
    return db.query(PhysicalValidationTrial).order_by(PhysicalValidationTrial.created_at.desc()).all()


@router.post("/research/benchmark-observations", response_model=BenchmarkObservationResponse, status_code=status.HTTP_201_CREATED, tags=["research-evaluation"])
def create_benchmark_observation(request: BenchmarkObservationCreate, db: Session = Depends(get_db)) -> BenchmarkObservation:
    observation = BenchmarkObservation(**request.model_dump())
    db.add(observation)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This benchmark case and variant are already recorded.") from exc
    db.refresh(observation)
    return observation


@router.get("/research/benchmark-observations", response_model=list[BenchmarkObservationResponse], tags=["research-evaluation"])
def list_benchmark_observations(benchmark_name: str | None = None, db: Session = Depends(get_db)) -> list[BenchmarkObservation]:
    query = db.query(BenchmarkObservation)
    if benchmark_name:
        query = query.filter(BenchmarkObservation.benchmark_name == benchmark_name)
    return query.order_by(BenchmarkObservation.created_at.desc()).all()


def _persist_research_run(db: Session, evaluation_type: str, configuration: dict, results: dict, provenance: dict) -> ResearchEvaluationRun:
    run = ResearchEvaluationRun(evaluation_type=evaluation_type, status=results["status"], configuration=configuration, results=results, provenance=provenance)
    db.add(run); db.flush()
    report_payload = {"run_id": run.id, "evaluation_type": evaluation_type, "configuration": configuration, "results": results, "provenance": provenance}
    path, digest = write_reproducible_report(Path(get_settings().storage_path) / "research_reports", run.id, report_payload)
    run.artifact_location, run.artifact_sha256 = path, digest
    db.commit(); db.refresh(run)
    return run


@router.post("/research/evaluations/physical", response_model=ResearchEvaluationRunResponse, status_code=status.HTTP_201_CREATED, tags=["research-evaluation"])
def create_physical_evaluation(request: PhysicalEvaluationCreate, db: Session = Depends(get_db)) -> ResearchEvaluationRun:
    trials = [db.get(PhysicalValidationTrial, trial_id) for trial_id in request.trial_ids]
    if any(trial is None for trial in trials):
        raise HTTPException(status_code=404, detail="Physical validation trial not found.")
    records = [{"predicted_benefit": trial.predicted_benefit, "observed_benefit": trial.observed_benefit} for trial in trials]
    results = summarize_physical_trials(records, request.minimum_trials)
    return _persist_research_run(db, "physical_validation", request.model_dump(), results, {"trial_ids": request.trial_ids})


@router.post("/research/evaluations/benchmark", response_model=ResearchEvaluationRunResponse, status_code=status.HTTP_201_CREATED, tags=["research-evaluation"])
def create_benchmark_evaluation(request: BenchmarkEvaluationCreate, db: Session = Depends(get_db)) -> ResearchEvaluationRun:
    query = db.query(BenchmarkObservation).filter(BenchmarkObservation.benchmark_name == request.benchmark_name)
    if request.observation_ids:
        query = query.filter(BenchmarkObservation.id.in_(request.observation_ids))
    observations = query.all()
    rows = [{
        "id": item.id, "case_id": item.case_id, "system_variant": item.system_variant,
        "recommendation_made": item.recommendation_made, "predicted_action": item.predicted_action,
        "ground_truth_action": item.ground_truth_action, "observed_harm": item.observed_harm,
        "uncertainty_handled": item.uncertainty_handled, "provenance_references": item.provenance_references,
    } for item in observations]
    results = evaluate_benchmark(rows, request.minimum_aligned_cases)
    return _persist_research_run(db, "comparative_benchmark", request.model_dump(), results, {"observation_ids": [item.id for item in observations], "benchmark_name": request.benchmark_name})


@router.get("/research/evaluations", response_model=list[ResearchEvaluationRunResponse], tags=["research-evaluation"])
def list_research_evaluations(db: Session = Depends(get_db)) -> list[ResearchEvaluationRun]:
    return db.query(ResearchEvaluationRun).order_by(ResearchEvaluationRun.created_at.desc()).all()


def _machine_or_404(machine_id: str, db: Session) -> Machine:
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found.")
    return machine


@router.post("/machines/{machine_id}/readings", response_model=SensorReadingResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance"])
def record_reading(machine_id: str, request: SensorReadingCreate, db: Session = Depends(get_db)) -> SensorReading:
    _machine_or_404(machine_id, db)
    reading = SensorReading(machine_id=machine_id, **request.model_dump())
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/machines/{machine_id}/readings", response_model=list[SensorReadingResponse], tags=["maintenance"])
def list_readings(machine_id: str, db: Session = Depends(get_db)) -> list[SensorReading]:
    _machine_or_404(machine_id, db)
    return db.query(SensorReading).filter(SensorReading.machine_id == machine_id).order_by(SensorReading.recorded_at.desc()).all()


@router.post("/machines/{machine_id}/fault-events", response_model=FaultEventResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance"])
def record_fault(machine_id: str, request: FaultEventCreate, db: Session = Depends(get_db)) -> FaultEvent:
    _machine_or_404(machine_id, db)
    event = FaultEvent(machine_id=machine_id, **request.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/machines/{machine_id}/fault-events", response_model=list[FaultEventResponse], tags=["maintenance"])
def list_faults(machine_id: str, db: Session = Depends(get_db)) -> list[FaultEvent]:
    _machine_or_404(machine_id, db)
    return db.query(FaultEvent).filter(FaultEvent.machine_id == machine_id).order_by(FaultEvent.observed_at.desc()).all()


@router.post("/machines/{machine_id}/maintenance-actions", response_model=MaintenanceActionResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance"])
def create_maintenance_action(machine_id: str, request: MaintenanceActionCreate, db: Session = Depends(get_db)) -> MaintenanceAction:
    _machine_or_404(machine_id, db)
    action = MaintenanceAction(machine_id=machine_id, **request.model_dump())
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


@router.get("/machines/{machine_id}/maintenance-actions", response_model=list[MaintenanceActionResponse], tags=["maintenance"])
def list_maintenance_actions(machine_id: str, db: Session = Depends(get_db)) -> list[MaintenanceAction]:
    _machine_or_404(machine_id, db)
    return db.query(MaintenanceAction).filter(MaintenanceAction.machine_id == machine_id).order_by(MaintenanceAction.scheduled_at.desc()).all()


def _verify_edge_token(token: str | None) -> None:
    expected = get_settings().edge_ingest_token
    if expected and (not token or not secrets.compare_digest(token, expected)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid edge ingestion token.")


@router.post("/machines/{machine_id}/signal-windows", response_model=SignalWindowResponse, status_code=status.HTTP_201_CREATED, tags=["signals"])
def record_signal_window(
    machine_id: str,
    request: SignalWindowCreate,
    db: Session = Depends(get_db),
    edge_token: str | None = Header(default=None, alias="X-Nexora-Edge-Token"),
) -> SignalWindow:
    _verify_edge_token(edge_token)
    _machine_or_404(machine_id, db)
    window = _create_signal_window(machine_id, request, db)
    db.commit()
    db.refresh(window)
    return window


def _create_signal_window(machine_id: str, request: SignalWindowCreate, db: Session) -> SignalWindow:
    result = extract_signal_features(request.samples, request.sample_rate_hz, smoothing_window=request.smoothing_window)
    window = SignalWindow(machine_id=machine_id, **request.model_dump(exclude={"smoothing_window"}))
    db.add(window)
    db.flush()
    window.feature_set = SignalFeatureSet(
        extractor_version=str(result.configuration["extractor_version"]),
        features=result.features,
        configuration=result.configuration,
    )
    db.flush()
    return window


@router.post("/edge/signal-windows", response_model=SignalWindowResponse, status_code=status.HTTP_201_CREATED, tags=["signals"])
def ingest_edge_signal_window(
    request: EdgeSignalEnvelope,
    db: Session = Depends(get_db),
    edge_token: str | None = Header(default=None, alias="X-Nexora-Edge-Token"),
) -> SignalWindow:
    _verify_edge_token(edge_token)
    receipt = db.query(EdgeIngestionReceipt).filter(EdgeIngestionReceipt.message_id == request.message_id).first()
    if receipt:
        if receipt.machine_id != request.machine_id:
            raise HTTPException(status_code=409, detail="Message ID is already associated with another machine.")
        return _signal_window_or_404(receipt.signal_window_id, db)
    _machine_or_404(request.machine_id, db)
    window_request = request.signal_window.model_copy(update={"source": "esp32_mqtt"})
    window = _create_signal_window(request.machine_id, window_request, db)
    db.add(EdgeIngestionReceipt(message_id=request.message_id, machine_id=request.machine_id, signal_window_id=window.id, transport="mqtt_bridge"))
    db.commit(); db.refresh(window)
    return window


@router.get("/machines/{machine_id}/signal-windows", response_model=list[SignalWindowResponse], tags=["signals"])
def list_signal_windows(machine_id: str, limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> list[SignalWindow]:
    _machine_or_404(machine_id, db)
    return db.query(SignalWindow).filter(SignalWindow.machine_id == machine_id).order_by(SignalWindow.recorded_at.desc()).limit(limit).all()


def _signal_window_or_404(signal_window_id: str, db: Session) -> SignalWindow:
    window = db.get(SignalWindow, signal_window_id)
    if not window:
        raise HTTPException(status_code=404, detail="Signal window not found.")
    return window


@router.put("/signal-windows/{signal_window_id}/label", response_model=SignalFaultLabelResponse, tags=["fault-models"])
def label_signal_window(signal_window_id: str, request: SignalFaultLabelCreate, db: Session = Depends(get_db)) -> SignalFaultLabel:
    _signal_window_or_404(signal_window_id, db)
    label = db.query(SignalFaultLabel).filter(SignalFaultLabel.signal_window_id == signal_window_id).one_or_none()
    if label:
        for key, value in request.model_dump().items():
            setattr(label, key, value)
    else:
        label = SignalFaultLabel(signal_window_id=signal_window_id, **request.model_dump())
        db.add(label)
    db.commit()
    db.refresh(label)
    return label


@router.get("/machines/{machine_id}/signal-labels", response_model=list[SignalFaultLabelResponse], tags=["fault-models"])
def list_signal_labels(machine_id: str, db: Session = Depends(get_db)) -> list[SignalFaultLabel]:
    _machine_or_404(machine_id, db)
    return db.query(SignalFaultLabel).join(SignalWindow).filter(SignalWindow.machine_id == machine_id).order_by(SignalFaultLabel.created_at.desc()).all()


@router.post("/fault-model-runs", response_model=FaultModelRunResponse, status_code=status.HTTP_201_CREATED, tags=["fault-models"])
def create_fault_model_run(request: FaultModelRunCreate, db: Session = Depends(get_db)) -> FaultModelRun:
    if request.machine_id:
        _machine_or_404(request.machine_id, db)
    query = db.query(SignalFaultLabel).join(SignalWindow).join(SignalFeatureSet)
    if request.machine_id:
        query = query.filter(SignalWindow.machine_id == request.machine_id)
    if request.confirmed_labels_only:
        query = query.filter(SignalFaultLabel.confirmed.is_(True))
    labels = query.all()
    run = FaultModelRun(machine_id=request.machine_id, status="running", configuration=request.model_dump(), results={}, feature_names=[], class_names=[])
    db.add(run)
    db.flush()
    try:
        results, winner, feature_names, class_names, artifact = train_fault_models(
            [item.signal_window.feature_set.features for item in labels],
            [item.fault_class for item in labels],
            artifact_dir=Path(get_settings().storage_path) / "fault_models" / run.id,
            random_seed=request.random_seed,
            test_size=request.test_size,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    run.status = "completed"
    run.results = results
    run.feature_names = feature_names
    run.class_names = class_names
    run.winning_model = winner
    run.artifact_location = artifact
    db.commit()
    db.refresh(run)
    return run


@router.get("/fault-model-runs", response_model=list[FaultModelRunResponse], tags=["fault-models"])
def list_fault_model_runs(db: Session = Depends(get_db)) -> list[FaultModelRun]:
    return db.query(FaultModelRun).order_by(FaultModelRun.created_at.desc()).all()


@router.post("/fault-model-runs/{model_run_id}/predictions", response_model=FaultPredictionResponse, status_code=status.HTTP_201_CREATED, tags=["fault-models"])
def create_fault_prediction(model_run_id: str, request: FaultPredictionCreate, db: Session = Depends(get_db)) -> FaultPrediction:
    run = db.get(FaultModelRun, model_run_id)
    if not run or run.status != "completed" or not run.artifact_location:
        raise HTTPException(status_code=404, detail="Completed fault model run not found.")
    window = _signal_window_or_404(request.signal_window_id, db)
    if not window.feature_set:
        raise HTTPException(status_code=422, detail="Signal window has no computed feature set.")
    try:
        predicted, confidence, probabilities = predict_fault(run.artifact_location, window.feature_set.features)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    prediction = FaultPrediction(model_run_id=run.id, signal_window_id=window.id, predicted_class=predicted, confidence=confidence, probabilities=probabilities, reliability_status="uncalibrated")
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


@router.post("/fault-predictions/{prediction_id}/explanation", response_model=FaultExplanationResponse, status_code=status.HTTP_201_CREATED, tags=["explainability"])
def create_fault_explanation(prediction_id: str, db: Session = Depends(get_db)) -> FaultExplanation:
    existing = db.query(FaultExplanation).filter(FaultExplanation.prediction_id == prediction_id).one_or_none()
    if existing:
        return existing
    prediction = db.get(FaultPrediction, prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Fault prediction not found.")
    run = db.get(FaultModelRun, prediction.model_run_id)
    window = db.get(SignalWindow, prediction.signal_window_id)
    if not run or not run.artifact_location or not window or not window.feature_set:
        raise HTTPException(status_code=422, detail="Prediction provenance is incomplete.")
    try:
        result = explain_fault_prediction(run.artifact_location, window.feature_set.features, prediction.predicted_class)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    explanation = FaultExplanation(prediction_id=prediction.id, **result)
    db.add(explanation)
    db.commit()
    db.refresh(explanation)
    return explanation


@router.post("/anomaly-model-runs", response_model=AnomalyModelRunResponse, status_code=status.HTTP_201_CREATED, tags=["anomaly-detection"])
def create_anomaly_model_run(request: AnomalyModelRunCreate, db: Session = Depends(get_db)) -> AnomalyModelRun:
    if request.machine_id:
        _machine_or_404(request.machine_id, db)
    query = db.query(SignalFaultLabel).join(SignalWindow).join(SignalFeatureSet).filter(SignalFaultLabel.confirmed.is_(True), SignalFaultLabel.fault_class == "normal")
    if request.machine_id:
        query = query.filter(SignalWindow.machine_id == request.machine_id)
    normal_labels = query.all()
    run = AnomalyModelRun(machine_id=request.machine_id, status="running", configuration=request.model_dump(), results={}, feature_names=[])
    db.add(run)
    db.flush()
    try:
        results, feature_names, artifact = train_anomaly_model(
            [item.signal_window.feature_set.features for item in normal_labels],
            artifact_dir=Path(get_settings().storage_path) / "anomaly_models" / run.id,
            random_seed=request.random_seed,
            contamination=request.contamination,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    run.status = "completed"
    run.results = results
    run.feature_names = feature_names
    run.artifact_location = artifact
    db.commit()
    db.refresh(run)
    return run


@router.get("/anomaly-model-runs", response_model=list[AnomalyModelRunResponse], tags=["anomaly-detection"])
def list_anomaly_model_runs(db: Session = Depends(get_db)) -> list[AnomalyModelRun]:
    return db.query(AnomalyModelRun).order_by(AnomalyModelRun.created_at.desc()).all()


@router.post("/anomaly-model-runs/{model_run_id}/scores", response_model=AnomalyScoreResponse, status_code=status.HTTP_201_CREATED, tags=["anomaly-detection"])
def create_anomaly_score(model_run_id: str, request: AnomalyScoreCreate, db: Session = Depends(get_db)) -> AnomalyScore:
    run = db.get(AnomalyModelRun, model_run_id)
    if not run or run.status != "completed" or not run.artifact_location:
        raise HTTPException(status_code=404, detail="Completed anomaly model run not found.")
    window = _signal_window_or_404(request.signal_window_id, db)
    if not window.feature_set:
        raise HTTPException(status_code=422, detail="Signal window has no computed feature set.")
    try:
        decision_score, is_anomaly = score_anomaly(run.artifact_location, window.feature_set.features)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    interpretation = "unknown_condition" if is_anomaly else "within_learned_normal_envelope"
    score = AnomalyScore(anomaly_model_run_id=run.id, signal_window_id=window.id, decision_score=decision_score, is_anomaly=is_anomaly, interpretation=interpretation)
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


@router.post("/machines/{machine_id}/maintenance-experiments", response_model=MaintenanceExperimentResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance-causal"])
def create_maintenance_experiment(machine_id: str, request: MaintenanceExperimentCreate, db: Session = Depends(get_db)) -> MaintenanceExperiment:
    _machine_or_404(machine_id, db)
    if request.source_window_ids:
        windows = db.query(SignalWindow).filter(SignalWindow.id.in_(request.source_window_ids)).all()
        if len(windows) != len(set(request.source_window_ids)) or any(window.machine_id != machine_id for window in windows):
            raise HTTPException(status_code=422, detail="Every source window must exist and belong to the experiment machine.")
    experiment = MaintenanceExperiment(machine_id=machine_id, **request.model_dump())
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


@router.get("/maintenance-experiments", response_model=list[MaintenanceExperimentResponse], tags=["maintenance-causal"])
def list_maintenance_experiments(intervention: str | None = None, db: Session = Depends(get_db)) -> list[MaintenanceExperiment]:
    query = db.query(MaintenanceExperiment)
    if intervention:
        query = query.filter(MaintenanceExperiment.intervention == intervention)
    return query.order_by(MaintenanceExperiment.recorded_at.desc()).all()


@router.post("/maintenance-causal-studies", response_model=MaintenanceCausalStudyResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance-causal"])
def create_maintenance_causal_study(request: MaintenanceCausalStudyCreate, db: Session = Depends(get_db)) -> MaintenanceCausalStudy:
    experiments = db.query(MaintenanceExperiment).filter(
        MaintenanceExperiment.intervention == request.intervention,
        MaintenanceExperiment.outcome_metric == request.outcome_metric,
        MaintenanceExperiment.confirmed.is_(True),
    ).all()
    records = [{"treatment_applied": item.treatment_applied, "pre_outcome": item.pre_outcome, "post_outcome": item.post_outcome, "covariates": item.covariates} for item in experiments]
    result = estimate_maintenance_effect(records, confounders=request.confounders, dag_edges=request.dag_edges, minimum_samples=request.minimum_samples)
    study = MaintenanceCausalStudy(
        intervention=request.intervention,
        outcome_metric=request.outcome_metric,
        status=result["validity_status"],
        configuration=request.model_dump(),
        result=result,
        estimated_effect=result.get("estimated_effect"),
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return study


@router.get("/maintenance-causal-studies", response_model=list[MaintenanceCausalStudyResponse], tags=["maintenance-causal"])
def list_maintenance_causal_studies(db: Session = Depends(get_db)) -> list[MaintenanceCausalStudy]:
    return db.query(MaintenanceCausalStudy).order_by(MaintenanceCausalStudy.created_at.desc()).all()


@router.post("/maintenance-causal-studies/{study_id}/counterfactuals", response_model=MaintenanceCounterfactualResponse, status_code=status.HTTP_201_CREATED, tags=["maintenance-causal"])
def create_maintenance_counterfactual(study_id: str, request: MaintenanceCounterfactualCreate, db: Session = Depends(get_db)) -> MaintenanceCounterfactual:
    study = db.get(MaintenanceCausalStudy, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Maintenance causal study not found.")
    _machine_or_404(request.machine_id, db)
    result = maintenance_counterfactual(
        study.result,
        current_outcome=request.current_outcome,
        apply_intervention=request.apply_intervention,
        feasible=request.feasible,
        infeasibility_reason=request.infeasibility_reason,
        lower_is_better=request.lower_is_better,
    )
    scenario = MaintenanceCounterfactual(causal_study_id=study.id, machine_id=request.machine_id, configuration=request.model_dump(), result=result, status=result["status"])
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.post("/fault-reliability-runs", response_model=FaultReliabilityRunResponse, status_code=status.HTTP_201_CREATED, tags=["reliability"])
def create_fault_reliability_run(request: FaultReliabilityRunCreate, db: Session = Depends(get_db)) -> FaultReliabilityRun:
    fault_run = db.get(FaultModelRun, request.fault_model_run_id)
    if not fault_run or fault_run.status != "completed" or not fault_run.artifact_location:
        raise HTTPException(status_code=404, detail="Completed fault model run not found.")
    run = FaultReliabilityRun(fault_model_run_id=fault_run.id, status="running", configuration=request.model_dump(), results={})
    db.add(run)
    db.flush()
    status_value, results, artifact = fit_reliability_model(
        fault_run.artifact_location,
        artifact_dir=Path(get_settings().storage_path) / "reliability_models" / run.id,
        alpha=request.alpha,
        minimum_calibration_size=request.minimum_calibration_size,
    )
    run.status = status_value
    run.results = results
    run.artifact_location = artifact
    db.commit()
    db.refresh(run)
    return run


@router.get("/fault-reliability-runs", response_model=list[FaultReliabilityRunResponse], tags=["reliability"])
def list_fault_reliability_runs(db: Session = Depends(get_db)) -> list[FaultReliabilityRun]:
    return db.query(FaultReliabilityRun).order_by(FaultReliabilityRun.created_at.desc()).all()


@router.post("/fault-reliability-runs/{reliability_run_id}/evaluations", response_model=SelectivePredictionResponse, status_code=status.HTTP_201_CREATED, tags=["reliability"])
def create_selective_prediction(reliability_run_id: str, request: SelectivePredictionCreate, db: Session = Depends(get_db)) -> SelectivePrediction:
    run = db.get(FaultReliabilityRun, reliability_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Reliability run not found.")
    prediction = db.get(FaultPrediction, request.fault_prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Fault prediction not found.")
    if prediction.model_run_id != run.fault_model_run_id:
        raise HTTPException(status_code=422, detail="Prediction and reliability run use different fault models.")
    anomaly = db.get(AnomalyScore, request.anomaly_score_id) if request.anomaly_score_id else None
    if request.anomaly_score_id and (not anomaly or anomaly.signal_window_id != prediction.signal_window_id):
        raise HTTPException(status_code=422, detail="Anomaly score must reference the prediction signal window.")
    if run.status != "calibrated" or not run.artifact_location:
        details = {"action": "ABSTAIN", "reasons": ["No valid independent calibration model."], "calibrated_probabilities": {}, "prediction_set": [], "anomaly_is_ood": bool(anomaly and anomaly.is_anomaly)}
    else:
        window = _signal_window_or_404(prediction.signal_window_id, db)
        try:
            details = evaluate_selective_prediction(run.artifact_location, window.feature_set.features, anomaly_is_ood=bool(anomaly and anomaly.is_anomaly), act_threshold=request.act_threshold, monitor_threshold=request.monitor_threshold)
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    evaluation = SelectivePrediction(
        reliability_run_id=run.id,
        fault_prediction_id=prediction.id,
        anomaly_score_id=anomaly.id if anomaly else None,
        action=details["action"],
        calibrated_probabilities=details["calibrated_probabilities"],
        prediction_set=details["prediction_set"],
        details=details,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


def _dataset_or_404(dataset_id: str, db: Session) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


def _frame(dataset: Dataset):
    return read_dataset(LocalDatasetStorage(get_settings().storage_path).path_for(dataset.filename))


@router.post("/datasets", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED, tags=["datasets"])
def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Dataset:
    suffix = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if suffix not in {"csv", "xlsx", "xls"}:
        raise HTTPException(status_code=415, detail="Only CSV and XLSX files are supported.")
    storage = LocalDatasetStorage(get_settings().storage_path)
    stored_name = storage.save(file)
    try:
        frame = read_dataset(storage.path_for(stored_name))
        profile = profile_dataframe(frame)
    except Exception:
        storage.delete(stored_name)
        raise HTTPException(status_code=422, detail="The uploaded file could not be parsed as a dataset.")
    dataset = Dataset(filename=stored_name, original_filename=file.filename or stored_name, row_count=len(frame), column_count=len(frame.columns), quality_score=profile["quality_score"], profile=profile)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/datasets", response_model=list[DatasetSummary], tags=["datasets"])
def list_datasets(db: Session = Depends(get_db)) -> list[Dataset]:
    return db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail, tags=["datasets"])
def dataset_details(dataset_id: str, db: Session = Depends(get_db)) -> Dataset:
    return _dataset_or_404(dataset_id, db)


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["datasets"])
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)) -> None:
    dataset = _dataset_or_404(dataset_id, db)
    LocalDatasetStorage(get_settings().storage_path).delete(dataset.filename)
    db.delete(dataset)
    db.commit()


@router.get("/datasets/{dataset_id}/preview", response_model=PreviewResponse, tags=["datasets"])
def dataset_preview(dataset_id: str, rows: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)) -> dict:
    frame = _frame(_dataset_or_404(dataset_id, db)).head(rows).where(lambda value: value.notna(), None)
    return {"columns": [str(column) for column in frame.columns], "rows": frame.to_dict(orient="records")}


@router.post("/datasets/{dataset_id}/cleaned-preview", response_model=PreviewResponse, tags=["datasets"])
def cleaned_preview(dataset_id: str, config: CleanedDatasetRequest, db: Session = Depends(get_db)) -> dict:
    """Returns a derived view only; the uploaded source file is never overwritten."""
    frame = cleaned_copy(_frame(_dataset_or_404(dataset_id, db)), config.model_dump()).head(100).where(lambda value: value.notna(), None)
    return {"columns": [str(column) for column in frame.columns], "rows": frame.to_dict(orient="records")}


@router.post("/datasets/{dataset_id}/analytics", tags=["analytics"])
def dataset_analytics(dataset_id: str, request: AnalyticsRequest, db: Session = Depends(get_db)) -> dict:
    frame = apply_filters(_frame(_dataset_or_404(dataset_id, db)), request.filters)
    try:
        grouped = aggregate(frame, request.measure, request.aggregation, request.dimension)
        trend = time_trend(frame, request.date_column, request.measure, request.aggregation) if request.date_column else []
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"kpi": aggregate(frame, request.measure, request.aggregation)[0]["value"], "breakdown": grouped, "trend": trend}


@router.post("/datasets/{dataset_id}/ml-runs", response_model=MLRunResponse, status_code=status.HTTP_201_CREATED, tags=["ml"])
def create_ml_run(dataset_id: str, request: MLRunRequest, db: Session = Depends(get_db)) -> MLRun:
    _dataset_or_404(dataset_id, db)
    run = MLRun(dataset_id=dataset_id, task=request.task, target=request.target, configuration=request.model_dump(), results={})
    db.add(run); db.flush()
    try:
        results, artifact = run_ml(_frame(_dataset_or_404(dataset_id, db)), request.model_dump(), Path("../model_artifacts/ml_runs") / run.id)
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=422, detail=str(exc)) from exc
    run.results, run.artifact_location = results, artifact
    db.commit(); db.refresh(run)
    return run


@router.get("/datasets/{dataset_id}/ml-runs", response_model=list[MLRunResponse], tags=["ml"])
def list_ml_runs(dataset_id: str, db: Session = Depends(get_db)) -> list[MLRun]:
    _dataset_or_404(dataset_id, db)
    return db.query(MLRun).filter(MLRun.dataset_id == dataset_id).order_by(MLRun.created_at.desc()).all()


@router.post("/datasets/{dataset_id}/causal-analyses", tags=["causal"])
def causal_analysis(dataset_id: str, request: CausalRequest, db: Session = Depends(get_db)) -> dict:
    """Produces estimator-derived effects only; raw correlation is never a causal claim."""
    _dataset_or_404(dataset_id, db)
    try:
     result=estimate_effect(_frame(_dataset_or_404(dataset_id, db)), request.treatment, request.outcome, request.confounders, request.treatment_type, request.dag_edges)
     run=CausalAnalysis(dataset_id=dataset_id,treatment=request.treatment,outcome=request.outcome,confounders={"values":request.confounders},estimator=result["estimator"],estimated_effect=result["estimated_effect"],result=result);db.add(run);db.commit();db.refresh(run);return {**result,"id":run.id}
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/scenarios/causal", tags=["scenarios"])
def causal_scenario(request: ScenarioRequest, db: Session = Depends(get_db)) -> dict:
    if request.variable != request.analysis_result.get("treatment"): raise HTTPException(status_code=422, detail="Scenario variable must equal the estimated treatment.")
    result=intervention_scenario(request.analysis_result, request.current_value, request.new_value)
    run=ScenarioRun(dataset_id=None,causal_analysis_id=request.analysis_result.get("id"),intervention={"variable":request.variable,"current_value":request.current_value,"new_value":request.new_value,"target_outcome":request.target_outcome},result=result,method_type="CAUSAL_INTERVENTION")
    db.add(run);db.commit();db.refresh(run);return {**result,"id":run.id}

@router.post("/decisions",tags=["decisions"])
def post_decision(request:DecisionRequest,db:Session=Depends(get_db)):
 evidence={"records":[item.model_dump() for item in request.evidence],"predictive_estimate":request.predictive_estimate,"predictive_uncertainty":request.predictive_uncertainty,"model_validation_performance":request.model_validation_performance,"data_quality":request.data_quality,"sample_size":request.sample_size,"provenance_references":request.provenance_references}
 return create_decision(db,request.question,request.decision_type,evidence,{},request.ecd_score)
@router.post("/decisions/integrated-maintenance",tags=["decisions"],status_code=status.HTTP_201_CREATED)
def post_integrated_maintenance_decision(request:IntegratedDecisionCreate,db:Session=Depends(get_db)):
 return create_integrated_decision(db,request.maintenance_plan_id,request.question)
@router.get("/decisions",tags=["decisions"])
def get_decisions(db:Session=Depends(get_db)): return db.query(Decision).order_by(Decision.created_at.desc()).all()
@router.get("/decisions/{decision_id}",tags=["decisions"])
def get_decision(decision_id:str,db:Session=Depends(get_db)): return _decision(decision_id,db)
@router.get("/decisions/{decision_id}/evidence",tags=["decisions"])
def decision_evidence(decision_id:str,db:Session=Depends(get_db)): return _decision(decision_id,db).evidence
@router.get("/decisions/{decision_id}/provenance",tags=["decisions"])
def decision_provenance(decision_id:str,db:Session=Depends(get_db)):
 d=_decision(decision_id,db);return {"root":db.get(ProvenanceNode,d.provenance_root_id),"edges":db.query(ProvenanceEdge).filter(ProvenanceEdge.target_node_id==d.provenance_root_id).all()}
@router.get("/decisions/{decision_id}/evidence-graph",tags=["decisions"])
def decision_evidence_graph(decision_id:str,db:Session=Depends(get_db)):
 _decision(decision_id,db)
 workflow=db.query(IntegratedDecisionWorkflow).filter(IntegratedDecisionWorkflow.decision_id==decision_id).first()
 if not workflow: raise HTTPException(status_code=404,detail="Integrated decision evidence graph not found.")
 return workflow.evidence_graph
@router.post("/decisions/{decision_id}/reviews",response_model=DecisionReviewResponse,tags=["decisions"],status_code=status.HTTP_201_CREATED)
def post_decision_review(decision_id:str,request:DecisionReviewCreate,db:Session=Depends(get_db)):
 return review_integrated_decision(db,decision_id,request.reviewer,request.outcome,request.notes)
@router.get("/decisions/{decision_id}/reviews",response_model=list[DecisionReviewResponse],tags=["decisions"])
def get_decision_reviews(decision_id:str,db:Session=Depends(get_db)):
 _decision(decision_id,db);return db.query(DecisionReview).filter(DecisionReview.decision_id==decision_id).order_by(DecisionReview.created_at.desc()).all()
def _decision(id,db):
 d=db.get(Decision,id)
 if not d: raise HTTPException(status_code=404,detail="Decision not found.")
 return d
@router.post("/investigator",tags=["investigator"])
def investigator(request:InvestigatorRequest,db:Session=Depends(get_db)):
 decision=_decision(request.decision_id,db) if request.decision_id else None
 records=list(decision.evidence) if decision else [db.get(DecisionEvidenceRecord,item) for item in request.evidence_ids]
 if any(item is None for item in records): raise HTTPException(status_code=404,detail="Evidence record not found.")
 gate={"status":decision.reliability_status if decision else "UNCALIBRATED" if request.ecd_score is None else "REVIEW"}
 evidence=[{"id":r.id,"type":r.evidence_type,"payload":r.payload,"uncertainty":r.uncertainty} for r in records]
 decision_payload={"id":decision.id,"recommendation":decision.recommendation} if decision else None
 result=investigate(request.question,evidence,gate,decision=decision_payload)
 return {"question":request.question,"intent":result["intent"],"status":gate["status"],"ecds":request.ecd_score,"review_required":decision.review_required if decision else True,"answer":result["explanation"],"evidence":result["provenance"],"provenance":result["provenance"],"decision_id":decision.id if decision else None}
