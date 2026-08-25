"""add physical validation and research evaluation

Revision ID: 0011_research_evaluation
Revises: 0010_integrated_decisions
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_research_evaluation"
down_revision = "0010_integrated_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "physical_validation_trials" not in existing:
        op.create_table(
            "physical_validation_trials",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("maintenance_action_id", sa.String(length=36), nullable=False),
            sa.Column("pre_reading_id", sa.String(length=36), nullable=False),
            sa.Column("post_reading_id", sa.String(length=36), nullable=False),
            sa.Column("outcome_metric", sa.String(length=32), nullable=False),
            sa.Column("predicted_benefit", sa.Float(), nullable=False), sa.Column("observed_benefit", sa.Float(), nullable=False),
            sa.Column("absolute_error", sa.Float(), nullable=False), sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("confirmed", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["maintenance_action_id"], ["maintenance_actions.id"]),
            sa.ForeignKeyConstraint(["pre_reading_id"], ["sensor_readings.id"]),
            sa.ForeignKeyConstraint(["post_reading_id"], ["sensor_readings.id"]), sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_physical_validation_trials_maintenance_action_id"), "physical_validation_trials", ["maintenance_action_id"], unique=False)
    if "benchmark_observations" not in existing:
        op.create_table(
            "benchmark_observations",
            sa.Column("id", sa.String(length=36), nullable=False), sa.Column("benchmark_name", sa.String(length=120), nullable=False),
            sa.Column("case_id", sa.String(length=120), nullable=False), sa.Column("system_variant", sa.String(length=64), nullable=False),
            sa.Column("recommendation_made", sa.Boolean(), nullable=False), sa.Column("predicted_action", sa.String(length=120)),
            sa.Column("ground_truth_action", sa.String(length=120), nullable=False), sa.Column("observed_harm", sa.Boolean(), nullable=False),
            sa.Column("uncertainty_handled", sa.Boolean(), nullable=False), sa.Column("provenance_references", sa.JSON(), nullable=False),
            sa.Column("evidence_source", sa.String(length=256), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("benchmark_name", "case_id", "system_variant"),
        )
        op.create_index(op.f("ix_benchmark_observations_benchmark_name"), "benchmark_observations", ["benchmark_name"], unique=False)
        op.create_index(op.f("ix_benchmark_observations_case_id"), "benchmark_observations", ["case_id"], unique=False)
        op.create_index(op.f("ix_benchmark_observations_system_variant"), "benchmark_observations", ["system_variant"], unique=False)
    if "research_evaluation_runs" not in existing:
        op.create_table(
            "research_evaluation_runs",
            sa.Column("id", sa.String(length=36), nullable=False), sa.Column("evaluation_type", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False), sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("results", sa.JSON(), nullable=False), sa.Column("provenance", sa.JSON(), nullable=False),
            sa.Column("artifact_location", sa.String(length=512)), sa.Column("artifact_sha256", sa.String(length=64)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "research_evaluation_runs" in existing: op.drop_table("research_evaluation_runs")
    if "benchmark_observations" in existing:
        op.drop_index(op.f("ix_benchmark_observations_system_variant"), table_name="benchmark_observations")
        op.drop_index(op.f("ix_benchmark_observations_case_id"), table_name="benchmark_observations")
        op.drop_index(op.f("ix_benchmark_observations_benchmark_name"), table_name="benchmark_observations")
        op.drop_table("benchmark_observations")
    if "physical_validation_trials" in existing:
        op.drop_index(op.f("ix_physical_validation_trials_maintenance_action_id"), table_name="physical_validation_trials")
        op.drop_table("physical_validation_trials")
