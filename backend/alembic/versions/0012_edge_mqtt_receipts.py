"""add idempotent edge MQTT ingestion receipts

Revision ID: 0012_edge_mqtt_receipts
Revises: 0011_research_evaluation
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_edge_mqtt_receipts"
down_revision = "0011_research_evaluation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "edge_ingestion_receipts" not in existing:
        op.create_table(
            "edge_ingestion_receipts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("message_id", sa.String(length=120), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=False),
            sa.Column("signal_window_id", sa.String(length=36), nullable=False),
            sa.Column("transport", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.ForeignKeyConstraint(["signal_window_id"], ["signal_windows.id"]),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("message_id"), sa.UniqueConstraint("signal_window_id"),
        )
        op.create_index(op.f("ix_edge_ingestion_receipts_message_id"), "edge_ingestion_receipts", ["message_id"], unique=True)
        op.create_index(op.f("ix_edge_ingestion_receipts_machine_id"), "edge_ingestion_receipts", ["machine_id"], unique=False)


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "edge_ingestion_receipts" in existing:
        op.drop_index(op.f("ix_edge_ingestion_receipts_machine_id"), table_name="edge_ingestion_receipts")
        op.drop_index(op.f("ix_edge_ingestion_receipts_message_id"), table_name="edge_ingestion_receipts")
        op.drop_table("edge_ingestion_receipts")
