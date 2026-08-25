"""add maintenance causal experiments and counterfactuals

Revision ID: 0006_maintenance_causal
Revises: 0005_explainability_anomaly
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_maintenance_causal"
down_revision = "0005_explainability_anomaly"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "maintenance_experiments" not in existing:
        op.create_table(
            "maintenance_experiments",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=False),
            sa.Column("intervention", sa.String(length=64), nullable=False),
            sa.Column("treatment_applied", sa.Boolean(), nullable=False),
            sa.Column("outcome_metric", sa.String(length=64), nullable=False),
            sa.Column("pre_outcome", sa.Float(), nullable=False),
            sa.Column("post_outcome", sa.Float(), nullable=False),
            sa.Column("covariates", sa.JSON(), nullable=False),
            sa.Column("confirmed", sa.Boolean(), nullable=False),
            sa.Column("source_window_ids", sa.JSON(), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_maintenance_experiments_machine_id"), "maintenance_experiments", ["machine_id"], unique=False)
        op.create_index(op.f("ix_maintenance_experiments_intervention"), "maintenance_experiments", ["intervention"], unique=False)
    if "maintenance_causal_studies" not in existing:
        op.create_table(
            "maintenance_causal_studies",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("intervention", sa.String(length=64), nullable=False),
            sa.Column("outcome_metric", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("estimated_effect", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if "maintenance_counterfactuals" not in existing:
        op.create_table(
            "maintenance_counterfactuals",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("causal_study_id", sa.String(length=36), nullable=False),
            sa.Column("machine_id", sa.String(length=36), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["causal_study_id"], ["maintenance_causal_studies.id"]),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_maintenance_counterfactuals_causal_study_id"), "maintenance_counterfactuals", ["causal_study_id"], unique=False)
        op.create_index(op.f("ix_maintenance_counterfactuals_machine_id"), "maintenance_counterfactuals", ["machine_id"], unique=False)


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "maintenance_counterfactuals" in existing:
        op.drop_index(op.f("ix_maintenance_counterfactuals_machine_id"), table_name="maintenance_counterfactuals")
        op.drop_index(op.f("ix_maintenance_counterfactuals_causal_study_id"), table_name="maintenance_counterfactuals")
        op.drop_table("maintenance_counterfactuals")
    if "maintenance_causal_studies" in existing:
        op.drop_table("maintenance_causal_studies")
    if "maintenance_experiments" in existing:
        op.drop_index(op.f("ix_maintenance_experiments_intervention"), table_name="maintenance_experiments")
        op.drop_index(op.f("ix_maintenance_experiments_machine_id"), table_name="maintenance_experiments")
        op.drop_table("maintenance_experiments")
