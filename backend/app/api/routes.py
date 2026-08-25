from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import text
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
from app.services.decisions import create_decision
from app.schemas.investigator import InvestigatorRequest
from app.services.investigator import investigate
from app.services.causal import estimate_effect, intervention_scenario
from app.schemas.causal import CausalRequest, ScenarioRequest
from pathlib import Path

router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", tags=["system"])
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


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
@router.get("/decisions",tags=["decisions"])
def get_decisions(db:Session=Depends(get_db)): return db.query(Decision).order_by(Decision.created_at.desc()).all()
@router.get("/decisions/{decision_id}",tags=["decisions"])
def get_decision(decision_id:str,db:Session=Depends(get_db)): return _decision(decision_id,db)
@router.get("/decisions/{decision_id}/evidence",tags=["decisions"])
def decision_evidence(decision_id:str,db:Session=Depends(get_db)): return _decision(decision_id,db).evidence
@router.get("/decisions/{decision_id}/provenance",tags=["decisions"])
def decision_provenance(decision_id:str,db:Session=Depends(get_db)):
 d=_decision(decision_id,db);return {"root":db.get(ProvenanceNode,d.provenance_root_id),"edges":db.query(ProvenanceEdge).filter(ProvenanceEdge.target_node_id==d.provenance_root_id).all()}
def _decision(id,db):
 d=db.get(Decision,id)
 if not d: raise HTTPException(status_code=404,detail="Decision not found.")
 return d
@router.post("/investigator",tags=["investigator"])
def investigator(request:InvestigatorRequest,db:Session=Depends(get_db)):
 records=[db.get(DecisionEvidenceRecord,item) for item in request.evidence_ids]
 if any(item is None for item in records): raise HTTPException(status_code=404,detail="Evidence record not found.")
 gate={"status":"UNCALIBRATED" if request.ecd_score is None else "REVIEW"}
 result=investigate(request.question,[{"type":r.evidence_type,**r.payload} for r in records],gate)
 return {"question":request.question,"intent":result["intent"],"status":gate["status"],"ecds":request.ecd_score,"review_required":True,"answer":result["explanation"],"evidence":result["provenance"],"provenance":result["provenance"]}
