from typing import Literal
from pydantic import BaseModel, Field


class MLRunRequest(BaseModel):
    task: Literal["regression", "binary_classification", "multiclass_classification", "forecasting", "clustering", "anomaly_detection"]
    target: str | None = None
    features: list[str] = Field(default_factory=list)
    test_size: float = Field(0.2, gt=0.05, lt=0.5)
    random_seed: int = 42
    time_column: str | None = None


class MLRunResponse(BaseModel):
    id: str
    dataset_id: str
    task: str
    target: str | None
    configuration: dict
    results: dict
    artifact_location: str | None

    model_config = {"from_attributes": True}
