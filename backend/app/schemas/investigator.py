from pydantic import BaseModel
class InvestigatorRequest(BaseModel): question:str; evidence_ids:list[str]=[]; ecd_score:float|None=None
