"""add fault explanations and anomaly detection

Revision ID: 0005_explainability_anomaly
Revises: 0004_fault_recognition
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_explainability_anomaly"
down_revision = "0004_fault_recognition"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "fault_explanations" not in existing:
        op.create_table(
            "fault_explanations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("prediction_id", sa.String(length=36), nullable=False),
            sa.Column("method", sa.String(length=64), nullable=False),
            sa.Column("explained_class", sa.String(length=64), nullable=False),
            sa.Column("base_value", sa.Float(), nullable=False),
            sa.Column("output_value", sa.Float(), nullable=False),
            sa.Column("contributions", sa.JSON(), nullable=False),
            sa.Column("feature_values", sa.JSON(), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["prediction_id"], ["fault_predictions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("prediction_id"),
        )
        op.create_index(op.f("ix_fault_explanations_prediction_id"), "fault_explanations", ["prediction_id"], unique=True)
    if "anomaly_model_runs" not in existing:
        op.create_table(
            "anomaly_model_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("results", sa.JSON(), nullable=False),
            sa.Column("feature_names", sa.JSON(), nullable=False),
            sa.Column("artifact_location", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_anomaly_model_runs_machine_id"), "anomaly_model_runs", ["machine_id"], unique=False)
    if "anomaly_scores" not in existing:
        op.create_table(
            "anomaly_scores",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("anomaly_model_run_id", sa.String(length=36), nullable=False),
            sa.Column("signal_window_id", sa.String(length=36), nullable=False),
            sa.Column("decision_score", sa.Float(), nullable=False),
            sa.Column("is_anomaly", sa.Boolean(), nullable=False),
            sa.Column("interpretation", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["anomaly_model_run_id"], ["anomaly_model_runs.id"]),
            sa.ForeignKeyConstraint(["signal_window_id"], ["signal_windows.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_anomaly_scores_anomaly_model_run_id"), "anomaly_scores", ["anomaly_model_run_id"], unique=False)
        op.create_index(op.f("ix_anomaly_scores_signal_window_id"), "anomaly_scores", ["signal_window_id"], unique=False)


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "anomaly_scores" in existing:
        op.drop_index(op.f("ix_anomaly_scores_signal_window_id"), table_name="anomaly_scores")
        op.drop_index(op.f("ix_anomaly_scores_anomaly_model_run_id"), table_name="anomaly_scores")
        op.drop_table("anomaly_scores")
    if "anomaly_model_runs" in existing:
        op.drop_index(op.f("ix_anomaly_model_runs_machine_id"), table_name="anomaly_model_runs")
        op.drop_table("anomaly_model_runs")
    if "fault_explanations" in existing:
        op.drop_index(op.f("ix_fault_explanations_prediction_id"), table_name="fault_explanations")
        op.drop_table("fault_explanations")
