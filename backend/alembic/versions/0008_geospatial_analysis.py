"""persist geospatial analysis runs

Revision ID: 0008_geospatial_analysis
Revises: 0007_fault_reliability
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_geospatial_analysis"
down_revision = "0007_fault_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "geospatial_analysis_runs" not in existing:
        op.create_table(
            "geospatial_analysis_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("analysis_type", sa.String(length=32), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "geospatial_analysis_runs" in existing:
        op.drop_table("geospatial_analysis_runs")
