"""add labelled windows and fault model runs

Revision ID: 0004_fault_recognition
Revises: 0003_signal_processing
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_fault_recognition"
down_revision = "0003_signal_processing"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "signal_fault_labels" not in existing:
        op.create_table(
            "signal_fault_labels",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("signal_window_id", sa.String(length=36), nullable=False),
            sa.Column("fault_class", sa.String(length=64), nullable=False),
            sa.Column("label_source", sa.String(length=64), nullable=False),
            sa.Column("confirmed", sa.Boolean(), nullable=False),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["signal_window_id"], ["signal_windows.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("signal_window_id"),
        )
        op.create_index(op.f("ix_signal_fault_labels_signal_window_id"), "signal_fault_labels", ["signal_window_id"], unique=True)
    if "fault_model_runs" not in existing:
        op.create_table(
            "fault_model_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("results", sa.JSON(), nullable=False),
            sa.Column("feature_names", sa.JSON(), nullable=False),
            sa.Column("class_names", sa.JSON(), nullable=False),
            sa.Column("winning_model", sa.String(length=64), nullable=True),
            sa.Column("artifact_location", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_fault_model_runs_machine_id"), "fault_model_runs", ["machine_id"], unique=False)
    if "fault_predictions" not in existing:
        op.create_table(
            "fault_predictions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("model_run_id", sa.String(length=36), nullable=False),
            sa.Column("signal_window_id", sa.String(length=36), nullable=False),
            sa.Column("predicted_class", sa.String(length=64), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("probabilities", sa.JSON(), nullable=False),
            sa.Column("reliability_status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["model_run_id"], ["fault_model_runs.id"]),
            sa.ForeignKeyConstraint(["signal_window_id"], ["signal_windows.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_fault_predictions_model_run_id"), "fault_predictions", ["model_run_id"], unique=False)
        op.create_index(op.f("ix_fault_predictions_signal_window_id"), "fault_predictions", ["signal_window_id"], unique=False)


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "fault_predictions" in existing:
        op.drop_index(op.f("ix_fault_predictions_signal_window_id"), table_name="fault_predictions")
        op.drop_index(op.f("ix_fault_predictions_model_run_id"), table_name="fault_predictions")
        op.drop_table("fault_predictions")
    if "fault_model_runs" in existing:
        op.drop_index(op.f("ix_fault_model_runs_machine_id"), table_name="fault_model_runs")
        op.drop_table("fault_model_runs")
    if "signal_fault_labels" in existing:
        op.drop_index(op.f("ix_signal_fault_labels_signal_window_id"), table_name="signal_fault_labels")
        op.drop_table("signal_fault_labels")
