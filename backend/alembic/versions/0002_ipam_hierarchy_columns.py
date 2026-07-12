"""Add IPAM hierarchy columns to databases created before Alembic.

Revision ID: 0002_ipam_hierarchy
Revises: 0001_initial_schema
"""
from alembic import op
import sqlalchemy as sa

revision="0002_ipam_hierarchy"
down_revision="0001_initial_schema"
branch_labels=None
depends_on=None

def upgrade():
    inspector=sa.inspect(op.get_bind())
    columns={column["name"] for column in inspector.get_columns("ipam_prefixes")}
    if "vrf_id" not in columns:
        op.add_column("ipam_prefixes",sa.Column("vrf_id",sa.String(length=36),nullable=True))
    if "parent_id" not in columns:
        op.add_column("ipam_prefixes",sa.Column("parent_id",sa.String(length=36),nullable=True))

def downgrade():
    # The initial schema already declares these columns for fresh databases.
    # Keeping them while stepping back to 0001 is therefore intentional; the
    # 0001 downgrade removes the complete table when returning to ``base``.
    pass
