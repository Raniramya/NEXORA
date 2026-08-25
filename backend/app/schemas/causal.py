from pydantic import BaseModel, Field

class CausalRequest(BaseModel):
    treatment: str; outcome: str; confounders: list[str] = Field(default_factory=list); effect_modifiers: list[str] = Field(default_factory=list); treatment_type: str; dag_edges: list[list[str]]

class ScenarioRequest(BaseModel):
    analysis_result: dict; variable: str; current_value: float; new_value: float; target_outcome: str
