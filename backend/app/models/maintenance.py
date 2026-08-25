import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), default="motor", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    readings = relationship("SensorReading", back_populates="machine", cascade="all, delete-orphan")
    fault_events = relationship("FaultEvent", back_populates="machine", cascade="all, delete-orphan")
    maintenance_actions = relationship("MaintenanceAction", back_populates="machine", cascade="all, delete-orphan")
    signal_windows = relationship("SignalWindow", back_populates="machine", cascade="all, delete-orphan")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vibration_rms: Mapped[float | None] = mapped_column(Float)
    temperature: Mapped[float | None] = mapped_column(Float)
    current: Mapped[float | None] = mapped_column(Float)
    rpm: Mapped[float | None] = mapped_column(Float)
    features: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    machine = relationship("Machine", back_populates="readings")


class FaultEvent(Base):
    __tablename__ = "fault_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    fault_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    machine = relationship("Machine", back_populates="fault_events")


class MaintenanceAction(Base):
    __tablename__ = "maintenance_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    predicted_benefit: Mapped[float | None] = mapped_column(Float)
    observed_benefit: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(String)

    machine = relationship("Machine", back_populates="maintenance_actions")


class SignalWindow(Base):
    __tablename__ = "signal_windows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sample_rate_hz: Mapped[float] = mapped_column(Float, nullable=False)
    channel: Mapped[str] = mapped_column(String(64), default="vibration", nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="g", nullable=False)
    samples: Mapped[list] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="esp32_http", nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(120))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    machine = relationship("Machine", back_populates="signal_windows")
    feature_set = relationship("SignalFeatureSet", back_populates="signal_window", cascade="all, delete-orphan", uselist=False)
    fault_label = relationship("SignalFaultLabel", back_populates="signal_window", cascade="all, delete-orphan", uselist=False)


class SignalFeatureSet(Base):
    __tablename__ = "signal_feature_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_window_id: Mapped[str] = mapped_column(ForeignKey("signal_windows.id"), nullable=False, unique=True, index=True)
    extractor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    signal_window = relationship("SignalWindow", back_populates="feature_set")


class EdgeIngestionReceipt(Base):
    __tablename__ = "edge_ingestion_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    signal_window_id: Mapped[str] = mapped_column(ForeignKey("signal_windows.id"), nullable=False, unique=True)
    transport: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SignalFaultLabel(Base):
    __tablename__ = "signal_fault_labels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_window_id: Mapped[str] = mapped_column(ForeignKey("signal_windows.id"), nullable=False, unique=True, index=True)
    fault_class: Mapped[str] = mapped_column(String(64), nullable=False)
    label_source: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    signal_window = relationship("SignalWindow", back_populates="fault_label")


class FaultModelRun(Base):
    __tablename__ = "fault_model_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    machine_id: Mapped[str | None] = mapped_column(ForeignKey("machines.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    results: Mapped[dict] = mapped_column(JSON, nullable=False)
    feature_names: Mapped[list] = mapped_column(JSON, nullable=False)
    class_names: Mapped[list] = mapped_column(JSON, nullable=False)
    winning_model: Mapped[str | None] = mapped_column(String(64))
    artifact_location: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FaultPrediction(Base):
    __tablename__ = "fault_predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_run_id: Mapped[str] = mapped_column(ForeignKey("fault_model_runs.id"), nullable=False, index=True)
    signal_window_id: Mapped[str] = mapped_column(ForeignKey("signal_windows.id"), nullable=False, index=True)
    predicted_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    probabilities: Mapped[dict] = mapped_column(JSON, nullable=False)
    reliability_status: Mapped[str] = mapped_column(String(32), default="uncalibrated", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FaultExplanation(Base):
    __tablename__ = "fault_explanations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prediction_id: Mapped[str] = mapped_column(ForeignKey("fault_predictions.id"), nullable=False, unique=True, index=True)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    explained_class: Mapped[str] = mapped_column(String(64), nullable=False)
    base_value: Mapped[float] = mapped_column(Float, nullable=False)
    output_value: Mapped[float] = mapped_column(Float, nullable=False)
    contributions: Mapped[dict] = mapped_column(JSON, nullable=False)
    feature_values: Mapped[dict] = mapped_column(JSON, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AnomalyModelRun(Base):
    __tablename__ = "anomaly_model_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    machine_id: Mapped[str | None] = mapped_column(ForeignKey("machines.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    results: Mapped[dict] = mapped_column(JSON, nullable=False)
    feature_names: Mapped[list] = mapped_column(JSON, nullable=False)
    artifact_location: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AnomalyScore(Base):
    __tablename__ = "anomaly_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    anomaly_model_run_id: Mapped[str] = mapped_column(ForeignKey("anomaly_model_runs.id"), nullable=False, index=True)
    signal_window_id: Mapped[str] = mapped_column(ForeignKey("signal_windows.id"), nullable=False, index=True)
    decision_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    interpretation: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaintenanceExperiment(Base):
    __tablename__ = "maintenance_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    intervention: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    treatment_applied: Mapped[bool] = mapped_column(Boolean, nullable=False)
    outcome_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    pre_outcome: Mapped[float] = mapped_column(Float, nullable=False)
    post_outcome: Mapped[float] = mapped_column(Float, nullable=False)
    covariates: Mapped[dict] = mapped_column(JSON, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_window_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaintenanceCausalStudy(Base):
    __tablename__ = "maintenance_causal_studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    intervention: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    estimated_effect: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaintenanceCounterfactual(Base):
    __tablename__ = "maintenance_counterfactuals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    causal_study_id: Mapped[str] = mapped_column(ForeignKey("maintenance_causal_studies.id"), nullable=False, index=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FaultReliabilityRun(Base):
    __tablename__ = "fault_reliability_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fault_model_run_id: Mapped[str] = mapped_column(ForeignKey("fault_model_runs.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    results: Mapped[dict] = mapped_column(JSON, nullable=False)
    artifact_location: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SelectivePrediction(Base):
    __tablename__ = "selective_predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reliability_run_id: Mapped[str] = mapped_column(ForeignKey("fault_reliability_runs.id"), nullable=False, index=True)
    fault_prediction_id: Mapped[str] = mapped_column(ForeignKey("fault_predictions.id"), nullable=False, index=True)
    anomaly_score_id: Mapped[str | None] = mapped_column(ForeignKey("anomaly_scores.id"), index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    calibrated_probabilities: Mapped[dict] = mapped_column(JSON, nullable=False)
    prediction_set: Mapped[list] = mapped_column(JSON, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GeospatialAnalysisRun(Base):
    __tablename__ = "geospatial_analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_type: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaintenanceOptimizationRun(Base):
    __tablename__ = "maintenance_optimization_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    results: Mapped[dict] = mapped_column(JSON, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaintenancePlan(Base):
    __tablename__ = "maintenance_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    optimization_run_id: Mapped[str] = mapped_column(ForeignKey("maintenance_optimization_runs.id"), nullable=False, index=True)
    solution_index: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    solution: Mapped[dict] = mapped_column(JSON, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
