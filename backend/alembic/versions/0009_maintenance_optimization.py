"""add evidence-bounded maintenance optimization

Revision ID: 0009_maintenance_optimization
Revises: 0008_geospatial_analysis
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_maintenance_optimization"
down_revision = "0008_geospatial_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "maintenance_optimization_runs" not in existing:
        op.create_table(
            "maintenance_optimization_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("results", sa.JSON(), nullable=False),
            sa.Column("provenance", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if "maintenance_plans" not in existing:
        op.create_table(
            "maintenance_plans",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("optimization_run_id", sa.String(length=36), nullable=False),
            sa.Column("solution_index", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("solution", sa.JSON(), nullable=False),
            sa.Column("provenance", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["optimization_run_id"], ["maintenance_optimization_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_maintenance_plans_optimization_run_id"), "maintenance_plans", ["optimization_run_id"], unique=False)


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "maintenance_plans" in existing:
        op.drop_index(op.f("ix_maintenance_plans_optimization_run_id"), table_name="maintenance_plans")
        op.drop_table("maintenance_plans")
    if "maintenance_optimization_runs" in existing:
        op.drop_table("maintenance_optimization_runs")
