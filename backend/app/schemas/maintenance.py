from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class MachineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    asset_type: str = "motor"
    status: str = "active"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    metadata_json: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together.")
        return self


class MachineResponse(MachineCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SensorReadingCreate(BaseModel):
    recorded_at: datetime
    vibration_rms: float | None = Field(default=None, ge=0)
    temperature: float | None = None
    current: float | None = Field(default=None, ge=0)
    rpm: float | None = Field(default=None, ge=0)
    features: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_measurement(self):
        if all(value is None for value in (self.vibration_rms, self.temperature, self.current, self.rpm)):
            raise ValueError("At least one sensor measurement is required.")
        return self


class SensorReadingResponse(SensorReadingCreate):
    id: str
    machine_id: str

    model_config = {"from_attributes": True}


class FaultEventCreate(BaseModel):
    fault_type: str = Field(min_length=1, max_length=64)
    severity: str = "unknown"
    confidence: float | None = Field(default=None, ge=0, le=1)
    observed_at: datetime
    evidence: dict = Field(default_factory=dict)


class FaultEventResponse(FaultEventCreate):
    id: str
    machine_id: str

    model_config = {"from_attributes": True}


class MaintenanceActionCreate(BaseModel):
    action_type: str = Field(min_length=1, max_length=64)
    status: str = "planned"
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    predicted_benefit: float | None = None
    observed_benefit: float | None = None
    notes: str | None = None


class MaintenanceActionResponse(MaintenanceActionCreate):
    id: str
    machine_id: str

    model_config = {"from_attributes": True}


class SignalWindowCreate(BaseModel):
    recorded_at: datetime
    sample_rate_hz: float = Field(gt=0, le=100_000)
    channel: str = Field(default="vibration", min_length=1, max_length=64)
    unit: str = Field(default="g", min_length=1, max_length=32)
    samples: list[float] = Field(min_length=8, max_length=100_000)
    source: str = Field(default="esp32_http", min_length=1, max_length=32)
    device_id: str | None = Field(default=None, max_length=120)
    smoothing_window: int = Field(default=1, ge=1, le=1000)
    metadata_json: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_window(self):
        if self.smoothing_window > len(self.samples):
            raise ValueError("Smoothing window cannot exceed the sample count.")
        return self


class SignalFeatureSetResponse(BaseModel):
    id: str
    signal_window_id: str
    extractor_version: str
    features: dict[str, float]
    configuration: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalWindowResponse(BaseModel):
    id: str
    machine_id: str
    recorded_at: datetime
    sample_rate_hz: float
    channel: str
    unit: str
    samples: list[float]
    source: str
    device_id: str | None
    metadata_json: dict
    created_at: datetime
    feature_set: SignalFeatureSetResponse

    model_config = {"from_attributes": True}


class EdgeSignalEnvelope(BaseModel):
    message_id: str = Field(min_length=1, max_length=120)
    machine_id: str
    signal_window: SignalWindowCreate


class SignalFaultLabelCreate(BaseModel):
    fault_class: str = Field(min_length=1, max_length=64)
    label_source: str = Field(min_length=1, max_length=64)
    confirmed: bool = False
    notes: str | None = None


class SignalFaultLabelResponse(SignalFaultLabelCreate):
    id: str
    signal_window_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FaultModelRunCreate(BaseModel):
    machine_id: str | None = None
    test_size: float = Field(default=0.25, ge=0.2, le=0.4)
    random_seed: int = 42
    confirmed_labels_only: bool = True


class FaultModelRunResponse(BaseModel):
    id: str
    machine_id: str | None
    status: str
    configuration: dict
    results: dict
    feature_names: list[str]
    class_names: list[str]
    winning_model: str | None
    artifact_location: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FaultPredictionCreate(BaseModel):
    signal_window_id: str


class FaultPredictionResponse(BaseModel):
    id: str
    model_run_id: str
    signal_window_id: str
    predicted_class: str
    confidence: float | None
    probabilities: dict[str, float]
    reliability_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FaultExplanationResponse(BaseModel):
    id: str
    prediction_id: str
    method: str
    explained_class: str
    base_value: float
    output_value: float
    contributions: dict[str, float]
    feature_values: dict[str, float]
    configuration: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AnomalyModelRunCreate(BaseModel):
    machine_id: str | None = None
    random_seed: int = 42
    contamination: float = Field(default=0.05, ge=0.01, le=0.2)


class AnomalyModelRunResponse(BaseModel):
    id: str
    machine_id: str | None
    status: str
    configuration: dict
    results: dict
    feature_names: list[str]
    artifact_location: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnomalyScoreCreate(BaseModel):
    signal_window_id: str


class AnomalyScoreResponse(BaseModel):
    id: str
    anomaly_model_run_id: str
    signal_window_id: str
    decision_score: float
    is_anomaly: bool
    interpretation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceExperimentCreate(BaseModel):
    intervention: str = Field(min_length=1, max_length=64)
    treatment_applied: bool
    outcome_metric: str = Field(min_length=1, max_length=64)
    pre_outcome: float
    post_outcome: float
    covariates: dict[str, float] = Field(default_factory=dict)
    confirmed: bool = False
    source_window_ids: list[str] = Field(default_factory=list)
    recorded_at: datetime


class MaintenanceExperimentResponse(MaintenanceExperimentCreate):
    id: str
    machine_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceCausalStudyCreate(BaseModel):
    intervention: str = Field(min_length=1, max_length=64)
    outcome_metric: str = Field(min_length=1, max_length=64)
    confounders: list[str] = Field(default_factory=list)
    dag_edges: list[list[str]]
    minimum_samples: int = Field(default=20, ge=10, le=10_000)


class MaintenanceCausalStudyResponse(BaseModel):
    id: str
    intervention: str
    outcome_metric: str
    status: str
    configuration: dict
    result: dict
    estimated_effect: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceCounterfactualCreate(BaseModel):
    machine_id: str
    current_outcome: float
    apply_intervention: bool = True
    feasible: bool = True
    infeasibility_reason: str | None = None
    lower_is_better: bool = True


class MaintenanceCounterfactualResponse(BaseModel):
    id: str
    causal_study_id: str
    machine_id: str
    configuration: dict
    result: dict
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FaultReliabilityRunCreate(BaseModel):
    fault_model_run_id: str
    alpha: float = Field(default=0.1, ge=0.01, le=0.3)
    minimum_calibration_size: int = Field(default=20, ge=10, le=10_000)


class FaultReliabilityRunResponse(BaseModel):
    id: str
    fault_model_run_id: str
    status: str
    configuration: dict
    results: dict
    artifact_location: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SelectivePredictionCreate(BaseModel):
    fault_prediction_id: str
    anomaly_score_id: str | None = None
    act_threshold: float = Field(default=0.8, ge=0.5, le=1)
    monitor_threshold: float = Field(default=0.5, ge=0, le=0.8)

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.monitor_threshold > self.act_threshold:
            raise ValueError("Monitor threshold cannot exceed ACT threshold.")
        return self


class SelectivePredictionResponse(BaseModel):
    id: str
    reliability_run_id: str
    fault_prediction_id: str
    anomaly_score_id: str | None
    action: str
    calibrated_probabilities: dict[str, float]
    prediction_set: list[str]
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetMapItem(BaseModel):
    machine_id: str
    machine_name: str
    status: str
    latitude: float
    longitude: float
    fault_event_count: int
    latest_fault_type: str | None


class DistanceRequest(BaseModel):
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)


class DistanceItem(BaseModel):
    machine_id: str
    machine_name: str
    distance_km: float


class HotspotAnalysisCreate(BaseModel):
    epsilon_km: float = Field(default=1.0, gt=0, le=1000)
    minimum_assets: int = Field(default=2, ge=2, le=100)
    lookback_days: int = Field(default=30, ge=1, le=3650)


class GeospatialAnalysisRunResponse(BaseModel):
    id: str
    analysis_type: str
    configuration: dict
    result: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class OptimizationCandidateCreate(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=64)
    machine_id: str
    selective_prediction_id: str
    counterfactual_id: str
    action_type: str = Field(min_length=1, max_length=64)
    cost: float = Field(ge=0)
    downtime_hours: float = Field(ge=0)
    duration_hours: float = Field(gt=0)


class MaintenanceOptimizationCreate(BaseModel):
    distance_analysis_run_id: str
    candidates: list[OptimizationCandidateCreate] = Field(min_length=1, max_length=100)
    budget: float = Field(gt=0)
    max_downtime_hours: float = Field(gt=0)
    technician_hours: float = Field(gt=0)
    max_actions: int = Field(gt=0, le=100)
    population_size: int = Field(default=80, ge=4, le=500)
    generations: int = Field(default=100, ge=1, le=2000)
    random_seed: int = 42

    @model_validator(mode="after")
    def unique_candidate_ids(self):
        identifiers = [candidate.candidate_id for candidate in self.candidates]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Candidate IDs must be unique within an optimization run.")
        return self


class MaintenanceOptimizationRunResponse(BaseModel):
    id: str
    status: str
    configuration: dict
    results: dict
    provenance: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenancePlanCreate(BaseModel):
    solution_index: int = Field(ge=0)


class MaintenancePlanResponse(BaseModel):
    id: str
    optimization_run_id: str
    solution_index: int
    status: str
    solution: dict
    provenance: dict
    created_at: datetime

    model_config = {"from_attributes": True}
