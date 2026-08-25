"""add raw signal windows and derived feature provenance

Revision ID: 0003_signal_processing
Revises: 0002_maintenance_foundation
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_signal_processing"
down_revision = "0002_maintenance_foundation"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "signal_windows" not in existing:
        op.create_table(
            "signal_windows",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sample_rate_hz", sa.Float(), nullable=False),
            sa.Column("channel", sa.String(length=64), nullable=False),
            sa.Column("unit", sa.String(length=32), nullable=False),
            sa.Column("samples", sa.JSON(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("device_id", sa.String(length=120), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_signal_windows_machine_id"), "signal_windows", ["machine_id"], unique=False)
    if "signal_feature_sets" not in existing:
        op.create_table(
            "signal_feature_sets",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("signal_window_id", sa.String(length=36), nullable=False),
            sa.Column("extractor_version", sa.String(length=64), nullable=False),
            sa.Column("features", sa.JSON(), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["signal_window_id"], ["signal_windows.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("signal_window_id"),
        )
        op.create_index(op.f("ix_signal_feature_sets_signal_window_id"), "signal_feature_sets", ["signal_window_id"], unique=True)


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "signal_feature_sets" in existing:
        op.drop_index(op.f("ix_signal_feature_sets_signal_window_id"), table_name="signal_feature_sets")
        op.drop_table("signal_feature_sets")
    if "signal_windows" in existing:
        op.drop_index(op.f("ix_signal_windows_machine_id"), table_name="signal_windows")
        op.drop_table("signal_windows")
