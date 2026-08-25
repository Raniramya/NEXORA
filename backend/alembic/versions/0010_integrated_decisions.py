"""add integrated decision workflow and review audit

Revision ID: 0010_integrated_decisions
Revises: 0009_maintenance_optimization
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_integrated_decisions"
down_revision = "0009_maintenance_optimization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "integrated_decision_workflows" not in existing:
        op.create_table(
            "integrated_decision_workflows",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("decision_id", sa.String(length=36), nullable=False),
            sa.Column("maintenance_plan_id", sa.String(length=36), nullable=False),
            sa.Column("readiness_status", sa.String(length=32), nullable=False),
            sa.Column("evidence_graph", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"]),
            sa.ForeignKeyConstraint(["maintenance_plan_id"], ["maintenance_plans.id"]),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("decision_id"), sa.UniqueConstraint("maintenance_plan_id"),
        )
        op.create_index(op.f("ix_integrated_decision_workflows_decision_id"), "integrated_decision_workflows", ["decision_id"], unique=True)
        op.create_index(op.f("ix_integrated_decision_workflows_maintenance_plan_id"), "integrated_decision_workflows", ["maintenance_plan_id"], unique=True)
    if "decision_reviews" not in existing:
        op.create_table(
            "decision_reviews",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("decision_id", sa.String(length=36), nullable=False),
            sa.Column("reviewer", sa.String(length=120), nullable=False),
            sa.Column("outcome", sa.String(length=32), nullable=False),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("created_action_ids", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"]), sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_decision_reviews_decision_id"), "decision_reviews", ["decision_id"], unique=False)


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "decision_reviews" in existing:
        op.drop_index(op.f("ix_decision_reviews_decision_id"), table_name="decision_reviews")
        op.drop_table("decision_reviews")
    if "integrated_decision_workflows" in existing:
        op.drop_index(op.f("ix_integrated_decision_workflows_maintenance_plan_id"), table_name="integrated_decision_workflows")
        op.drop_index(op.f("ix_integrated_decision_workflows_decision_id"), table_name="integrated_decision_workflows")
        op.drop_table("integrated_decision_workflows")
