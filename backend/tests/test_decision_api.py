from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import app.models
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.dataset import Dataset
from app.services.decisions import create_decision

def test_decision_http_endpoints():
 engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool);Base.metadata.create_all(engine);Session=sessionmaker(bind=engine);db=Session()
 dataset=Dataset(filename="api.csv",original_filename="api.csv",row_count=1,column_count=1,quality_score=100,profile={});db.add(dataset);db.commit()
 payload={"records":[{"evidence_type":"analytics","source_type":"dataset","source_id":dataset.id,"dataset_id":dataset.id,"payload":{},"uncertainty":{},"metadata_json":{}}],"predictive_estimate":None,"predictive_uncertainty":None,"model_validation_performance":None,"data_quality":None,"sample_size":None,"provenance_references":[]}
 decision=create_decision(db,"API question","prescriptive",payload,{},None)
 def override():
  try: yield db
  finally: pass
 app.dependency_overrides[get_db]=override
 client=TestClient(app)
 detail=client.get(f"/api/decisions/{decision.id}");assert detail.status_code==200 and detail.json()["id"]==decision.id and detail.json()["review_required"]
 evidence=client.get(f"/api/decisions/{decision.id}/evidence");assert evidence.status_code==200 and evidence.json()[0]["source_id"]==dataset.id
 provenance=client.get(f"/api/decisions/{decision.id}/provenance");assert provenance.status_code==200 and provenance.json()["root"] and provenance.json()["edges"]
 for path in [f"/api/decisions/00000000-0000-0000-0000-000000000000",f"/api/decisions/00000000-0000-0000-0000-000000000000/evidence",f"/api/decisions/00000000-0000-0000-0000-000000000000/provenance"]: assert client.get(path).status_code==404
 app.dependency_overrides.clear();db.close()
