from datetime import datetime
from typing import Literal

from pydantic import BaseModel,Field
class EvidenceInput(BaseModel): evidence_type:str;source_type:str;source_id:str|None=None;dataset_id:str|None=None;payload:dict;uncertainty:dict=Field(default_factory=dict);metadata_json:dict=Field(default_factory=dict)
class DecisionRequest(BaseModel): question:str;decision_type:str="prescriptive";evidence:list[EvidenceInput];predictive_estimate:float|None=None;predictive_uncertainty:float|None=None;model_validation_performance:float|None=None;data_quality:float|None=None;sample_size:int|None=None;provenance_references:list[str]=Field(default_factory=list);ecd_score:float|None=None


class IntegratedDecisionCreate(BaseModel):
    maintenance_plan_id: str
    question: str = Field(min_length=3, max_length=500)


class DecisionReviewCreate(BaseModel):
    reviewer: str = Field(min_length=2, max_length=120)
    outcome: Literal["approved", "rejected"]
    notes: str | None = Field(default=None, max_length=2000)


class DecisionReviewResponse(BaseModel):
    id: str
    decision_id: str
    reviewer: str
    outcome: str
    notes: str | None
    created_action_ids: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
