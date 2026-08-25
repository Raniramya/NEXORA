"""add calibrated fault reliability and selective predictions

Revision ID: 0007_fault_reliability
Revises: 0006_maintenance_causal
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_fault_reliability"
down_revision = "0006_maintenance_causal"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "fault_reliability_runs" not in existing:
        op.create_table(
            "fault_reliability_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("fault_model_run_id", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("results", sa.JSON(), nullable=False),
            sa.Column("artifact_location", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["fault_model_run_id"], ["fault_model_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_fault_reliability_runs_fault_model_run_id"), "fault_reliability_runs", ["fault_model_run_id"], unique=False)
    if "selective_predictions" not in existing:
        op.create_table(
            "selective_predictions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("reliability_run_id", sa.String(length=36), nullable=False),
            sa.Column("fault_prediction_id", sa.String(length=36), nullable=False),
            sa.Column("anomaly_score_id", sa.String(length=36), nullable=True),
            sa.Column("action", sa.String(length=32), nullable=False),
            sa.Column("calibrated_probabilities", sa.JSON(), nullable=False),
            sa.Column("prediction_set", sa.JSON(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["reliability_run_id"], ["fault_reliability_runs.id"]),
            sa.ForeignKeyConstraint(["fault_prediction_id"], ["fault_predictions.id"]),
            sa.ForeignKeyConstraint(["anomaly_score_id"], ["anomaly_scores.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_selective_predictions_reliability_run_id"), "selective_predictions", ["reliability_run_id"], unique=False)
        op.create_index(op.f("ix_selective_predictions_fault_prediction_id"), "selective_predictions", ["fault_prediction_id"], unique=False)
        op.create_index(op.f("ix_selective_predictions_anomaly_score_id"), "selective_predictions", ["anomaly_score_id"], unique=False)


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "selective_predictions" in existing:
        op.drop_index(op.f("ix_selective_predictions_anomaly_score_id"), table_name="selective_predictions")
        op.drop_index(op.f("ix_selective_predictions_fault_prediction_id"), table_name="selective_predictions")
        op.drop_index(op.f("ix_selective_predictions_reliability_run_id"), table_name="selective_predictions")
        op.drop_table("selective_predictions")
    if "fault_reliability_runs" in existing:
        op.drop_index(op.f("ix_fault_reliability_runs_fault_model_run_id"), table_name="fault_reliability_runs")
        op.drop_table("fault_reliability_runs")
