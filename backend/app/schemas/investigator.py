from pydantic import BaseModel, Field
class InvestigatorRequest(BaseModel): question:str; evidence_ids:list[str]=Field(default_factory=list); decision_id:str|None=None; ecd_score:float|None=None
