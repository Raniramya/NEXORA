from app.models.decision import Decision,DecisionEvidenceRecord,ProvenanceNode,ProvenanceEdge
from app.services.reliability import decision_gate
from app.models.dataset import Dataset
from app.models.ml_run import MLRun
from app.models.causal_run import CausalAnalysis, ScenarioRun, ReliabilityEvaluation
from fastapi import HTTPException

def validate_sources(db, records):
 models={"dataset":Dataset,"ml_run":MLRun,"causal_analysis":CausalAnalysis,"scenario":ScenarioRun,"reliability_evaluation":ReliabilityEvaluation}
 for item in records:
  source=item["source_type"]; source_id=item.get("source_id")
  if source not in models: raise HTTPException(status_code=422,detail=f"Unsupported evidence source type: {source}")
  if not source_id: raise HTTPException(status_code=422,detail="Evidence source_id is required.")
  if not db.get(models[source],source_id): raise HTTPException(status_code=404,detail=f"Referenced {source} not found.")

def create_decision(db,question,decision_type,evidence,reliability,ecd_score=None):
 validate_sources(db,evidence.get("records",[]))
 gate=decision_gate(ecd_score,evidence); records=[]
 evaluation=ReliabilityEvaluation(decision_id=None,status=gate["status"],ecds=ecd_score,details={"gate":gate,"completeness":evidence});db.add(evaluation);db.flush()
 for item in evidence.get("records",[]):
  record=DecisionEvidenceRecord(**item);db.add(record);records.append(record)
 db.flush(); root=ProvenanceNode(node_type="decision",resource_type="decision",resource_id=None,metadata_json={"status":gate["status"]});db.add(root);db.flush()
 for record in records:
  node=ProvenanceNode(node_type="evidence",resource_type="evidence",resource_id=record.id,metadata_json={"type":record.evidence_type});db.add(node);db.flush();db.add(ProvenanceEdge(source_node_id=node.id,target_node_id=root.id,relation_type="USED_IN_DECISION"))
 recommendation=None if gate["status"] in {"ABSTAIN","UNCALIBRATED"} else "Advisory recommendation based on referenced evidence."
 decision=Decision(question=question,decision_type=decision_type,recommendation=recommendation,reliability_status=gate["status"],ecds=ecd_score,review_required=gate["status"] in {"REVIEW","UNCALIBRATED"},abstention_reason="; ".join(gate["reasons"]) or None,reliability_details={**gate,"reliability_evaluation_id":evaluation.id},provenance_root_id=root.id,evidence=records);db.add(decision);db.flush();evaluation.decision_id=decision.id;db.commit();db.refresh(decision);return decision
