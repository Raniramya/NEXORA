"""initial schema
Revision ID: 0001_initial
"""
revision="0001_initial"; down_revision=None; branch_labels=None; depends_on=None
def upgrade():
 from app.db.base import Base
 import app.models
 from alembic import op
 Base.metadata.create_all(op.get_bind())
def downgrade():
 from app.db.base import Base
 from alembic import op
 Base.metadata.drop_all(op.get_bind())
