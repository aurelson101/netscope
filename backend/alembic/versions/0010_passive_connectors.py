"""Add authenticated passive discovery connectors."""
from alembic import op
import sqlalchemy as sa

revision="0010_passive_connectors"
down_revision="0009_scan_progress"
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind();tables=set(sa.inspect(bind).get_table_names())
    if "scan_profiles" in tables:op.execute("UPDATE scan_profiles SET name='Résolution DNS ciblée' WHERE name='Découverte passive' AND NOT EXISTS (SELECT 1 FROM scan_profiles WHERE name='Résolution DNS ciblée')")
    if "passive_connectors" not in tables:
        op.create_table("passive_connectors",sa.Column("id",sa.String(36),primary_key=True),sa.Column("name",sa.String(120),nullable=False,unique=True),sa.Column("kind",sa.String(30),nullable=False),sa.Column("token_hash",sa.String(64),nullable=False,unique=True),sa.Column("vrf_id",sa.String(36),sa.ForeignKey("vrfs.id"),nullable=True),sa.Column("enabled",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("event_count",sa.Integer(),nullable=False,server_default="0"),sa.Column("last_seen_at",sa.DateTime(timezone=True),nullable=True),sa.Column("last_error",sa.Text(),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
        op.create_index("ix_passive_connectors_vrf_id","passive_connectors",["vrf_id"])
    if "passive_event_receipts" not in tables:
        op.create_table("passive_event_receipts",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("connector_id",sa.String(36),sa.ForeignKey("passive_connectors.id"),nullable=False),sa.Column("event_id",sa.String(120),nullable=False),sa.Column("received_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("connector_id","event_id",name="uq_passive_event_connector_event"))
        op.create_index("ix_passive_event_receipts_connector_id","passive_event_receipts",["connector_id"])

def downgrade():
    tables=set(sa.inspect(op.get_bind()).get_table_names())
    if "passive_event_receipts" in tables:op.drop_table("passive_event_receipts")
    if "passive_connectors" in tables:op.drop_table("passive_connectors")
    if "scan_profiles" in tables:op.execute("UPDATE scan_profiles SET name='Découverte passive' WHERE name='Résolution DNS ciblée' AND NOT EXISTS (SELECT 1 FROM scan_profiles WHERE name='Découverte passive')")
