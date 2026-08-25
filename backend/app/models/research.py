import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PhysicalValidationTrial(Base):
    __tablename__ = "physical_validation_trials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    maintenance_action_id: Mapped[str] = mapped_column(ForeignKey("maintenance_actions.id"), nullable=False, index=True)
    pre_reading_id: Mapped[str] = mapped_column(ForeignKey("sensor_readings.id"), nullable=False)
    post_reading_id: Mapped[str] = mapped_column(ForeignKey("sensor_readings.id"), nullable=False)
    outcome_metric: Mapped[str] = mapped_column(String(32), nullable=False)
    predicted_benefit: Mapped[float] = mapped_column(Float, nullable=False)
    observed_benefit: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_error: Mapped[float] = mapped_column(Float, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BenchmarkObservation(Base):
    __tablename__ = "benchmark_observations"
    __table_args__ = (UniqueConstraint("benchmark_name", "case_id", "system_variant"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    benchmark_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    system_variant: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recommendation_made: Mapped[bool] = mapped_column(Boolean, nullable=False)
    predicted_action: Mapped[str | None] = mapped_column(String(120))
    ground_truth_action: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_harm: Mapped[bool] = mapped_column(Boolean, nullable=False)
    uncertainty_handled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance_references: Mapped[list] = mapped_column(JSON, nullable=False)
    evidence_source: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ResearchEvaluationRun(Base):
    __tablename__ = "research_evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    results: Mapped[dict] = mapped_column(JSON, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    artifact_location: Mapped[str | None] = mapped_column(String(512))
    artifact_sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
