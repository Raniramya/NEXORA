import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.db.base import Base
from app.models.dataset import Dataset
from app.models.ml_run import MLRun
from app.models.causal_run import CausalAnalysis, ScenarioRun, ReliabilityEvaluation
from app.models.decision import DecisionEvidenceRecord
from app.services.decisions import create_decision, validate_sources
from app.services.investigator import investigate

@pytest.fixture()
def db():
 engine=create_engine("sqlite://");Base.metadata.create_all(engine);session=sessionmaker(bind=engine)();yield session;session.close()

def seed(db):
 d=Dataset(filename="x.csv",original_filename="x.csv",row_count=1,column_count=1,quality_score=100,profile={});db.add(d);db.flush()
 m=MLRun(dataset_id=d.id,task="regression",target="y",configuration={},results={},artifact_location=None)
 c=CausalAnalysis(dataset_id=d.id,treatment="a",outcome="y",confounders={},estimator="linear",estimated_effect=1,result={})
 s=ScenarioRun(dataset_id=d.id,causal_analysis_id=None,intervention={},result={"kind":"predictive_scenario"},method_type="PREDICTIVE_SCENARIO")
 r=ReliabilityEvaluation(decision_id=None,status="UNCALIBRATED",ecds=None,details={})
 db.add_all([m,c,s,r]);db.commit();return d,m,c,s,r

def evidence(source,id): return {"evidence_type":"test","source_type":source,"source_id":id,"dataset_id":None,"payload":{"client":"ignored"},"uncertainty":{},"metadata_json":{}}

def test_all_authoritative_sources_and_gate(db):
 d,m,c,s,r=seed(db)
 for name,obj in [("dataset",d),("ml_run",m),("causal_analysis",c),("scenario",s),("reliability_evaluation",r)]: validate_sources(db,[evidence(name,obj.id)])
 with pytest.raises(HTTPException): validate_sources(db,[evidence("dataset","missing")])
 with pytest.raises(HTTPException): validate_sources(db,[evidence("unknown",d.id)])
 payload={"records":[evidence("dataset",d.id)],"predictive_estimate":None,"predictive_uncertainty":None,"model_validation_performance":None,"data_quality":None,"sample_size":None,"provenance_references":[]}
 decision=create_decision(db,"q","prescriptive",payload,{},None)
 assert decision.reliability_status=="UNCALIBRATED" and decision.review_required and decision.recommendation is None and decision.evidence and decision.provenance_root_id
 assert db.query(DecisionEvidenceRecord).count()==1
 assert s.method_type=="PREDICTIVE_SCENARIO"

def test_investigator_abstain_is_deterministic():
 result=investigate("cause?",[{"type":"causal","effect":1}],{"status":"ABSTAIN"})
 assert "no recommendation" in result["explanation"] and result["provenance"]
