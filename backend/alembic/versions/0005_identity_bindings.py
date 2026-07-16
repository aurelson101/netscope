"""Add immutable network identity observations."""
from alembic import op
import sqlalchemy as sa

revision="0005_identity_bindings"
down_revision="0004_alert_constraints"
branch_labels=None
depends_on=None

def upgrade():
    if "network_identity_bindings" in sa.inspect(op.get_bind()).get_table_names():return
    op.create_table("network_identity_bindings",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("asset_id",sa.String(36),sa.ForeignKey("assets.id")),
        sa.Column("ip_address",sa.String(64),nullable=False),
        sa.Column("mac_address",sa.String(32)),
        sa.Column("source",sa.String(50),nullable=False),
        sa.Column("scan_id",sa.String(36),sa.ForeignKey("scan_jobs.id")),
        sa.Column("observed_at",sa.DateTime(timezone=True),nullable=False))
    for column in ("asset_id","ip_address","mac_address","scan_id","observed_at"):op.create_index(f"ix_network_identity_bindings_{column}","network_identity_bindings",[column])

def downgrade():
    if "network_identity_bindings" in sa.inspect(op.get_bind()).get_table_names():op.drop_table("network_identity_bindings")
