"""add physical maintenance foundation

Revision ID: 0002_maintenance_foundation
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_maintenance_foundation"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # The initial development migration historically used metadata.create_all().
    # Checking the live schema keeps upgrades safe for both fresh and existing DBs.
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "machines" not in existing:
        op.create_table(
            "machines",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("asset_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if "sensor_readings" not in existing:
        op.create_table(
            "sensor_readings",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("vibration_rms", sa.Float(), nullable=True),
            sa.Column("temperature", sa.Float(), nullable=True),
            sa.Column("current", sa.Float(), nullable=True),
            sa.Column("rpm", sa.Float(), nullable=True),
            sa.Column("features", sa.JSON(), nullable=False),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_sensor_readings_machine_id"), "sensor_readings", ["machine_id"], unique=False)
    if "fault_events" not in existing:
        op.create_table(
            "fault_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=False),
            sa.Column("fault_type", sa.String(length=64), nullable=False),
            sa.Column("severity", sa.String(length=32), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_fault_events_machine_id"), "fault_events", ["machine_id"], unique=False)
    if "maintenance_actions" not in existing:
        op.create_table(
            "maintenance_actions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=False),
            sa.Column("action_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("predicted_benefit", sa.Float(), nullable=True),
            sa.Column("observed_benefit", sa.Float(), nullable=True),
            sa.Column("notes", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_maintenance_actions_machine_id"), "maintenance_actions", ["machine_id"], unique=False)


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table, index in (
        ("maintenance_actions", "ix_maintenance_actions_machine_id"),
        ("fault_events", "ix_fault_events_machine_id"),
        ("sensor_readings", "ix_sensor_readings_machine_id"),
    ):
        if table in existing:
            op.drop_index(op.f(index), table_name=table)
            op.drop_table(table)
    if "machines" in existing:
        op.drop_table("machines")
