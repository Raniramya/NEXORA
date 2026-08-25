from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PhysicalValidationTrialCreate(BaseModel):
    maintenance_action_id: str
    pre_reading_id: str
    post_reading_id: str
    outcome_metric: Literal["vibration_rms", "temperature", "current", "rpm"]
    lower_is_better: bool = True
    confirmed: bool


class PhysicalValidationTrialResponse(BaseModel):
    id: str
    maintenance_action_id: str
    pre_reading_id: str
    post_reading_id: str
    outcome_metric: str
    predicted_benefit: float
    observed_benefit: float
    absolute_error: float
    result: dict
    confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BenchmarkObservationCreate(BaseModel):
    benchmark_name: str = Field(min_length=1, max_length=120)
    case_id: str = Field(min_length=1, max_length=120)
    system_variant: str = Field(min_length=1, max_length=64)
    recommendation_made: bool
    predicted_action: str | None = Field(default=None, max_length=120)
    ground_truth_action: str = Field(min_length=1, max_length=120)
    observed_harm: bool = False
    uncertainty_handled: bool = False
    provenance_references: list[str] = Field(default_factory=list)
    evidence_source: str = Field(min_length=1, max_length=256)
    metadata_json: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def recommendation_consistency(self):
        if self.recommendation_made and not self.predicted_action:
            raise ValueError("predicted_action is required when a recommendation was made.")
        if not self.recommendation_made and self.predicted_action is not None:
            raise ValueError("predicted_action must be absent for an abstention.")
        return self


class BenchmarkObservationResponse(BenchmarkObservationCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PhysicalEvaluationCreate(BaseModel):
    trial_ids: list[str] = Field(min_length=1)
    minimum_trials: int = Field(default=3, ge=2, le=10000)


class BenchmarkEvaluationCreate(BaseModel):
    benchmark_name: str
    observation_ids: list[str] = Field(default_factory=list)
    minimum_aligned_cases: int = Field(default=3, ge=2, le=10000)


class ResearchEvaluationRunResponse(BaseModel):
    id: str
    evaluation_type: str
    status: str
    configuration: dict
    results: dict
    provenance: dict
    artifact_location: str | None
    artifact_sha256: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
