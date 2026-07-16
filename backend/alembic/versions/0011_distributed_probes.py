"""Add outbound distributed probes and remote scan assignment."""
from alembic import op
import sqlalchemy as sa

revision="0011_distributed_probes"
down_revision="0010_passive_connectors"
branch_labels=None
depends_on=None

def upgrade():
    inspector=sa.inspect(op.get_bind());tables=set(inspector.get_table_names())
    if "probes" not in tables:
        op.create_table("probes",sa.Column("id",sa.String(36),primary_key=True),sa.Column("name",sa.String(120),nullable=False,unique=True),sa.Column("token_hash",sa.String(64),nullable=False,unique=True),sa.Column("site_id",sa.String(36),sa.ForeignKey("sites.id"),nullable=True),sa.Column("vrf_id",sa.String(36),sa.ForeignKey("vrfs.id"),nullable=True),sa.Column("enabled",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("capabilities",sa.JSON(),nullable=False),sa.Column("version",sa.String(40),nullable=True),sa.Column("last_seen_at",sa.DateTime(timezone=True),nullable=True),sa.Column("last_ip",sa.String(64),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
        op.create_index("ix_probes_site_id","probes",["site_id"]);op.create_index("ix_probes_vrf_id","probes",["vrf_id"])
    for table in ("scan_jobs","scan_schedules"):
        if table not in tables:continue
        columns={x["name"] for x in sa.inspect(op.get_bind()).get_columns(table)}
        if "probe_id" not in columns:op.add_column(table,sa.Column("probe_id",sa.String(36),sa.ForeignKey("probes.id"),nullable=True));op.create_index(f"ix_{table}_probe_id",table,["probe_id"])
    columns={x["name"] for x in sa.inspect(op.get_bind()).get_columns("scan_jobs")} if "scan_jobs" in tables else set()
    if "scan_jobs" in tables and "probe_claimed_at" not in columns:op.add_column("scan_jobs",sa.Column("probe_claimed_at",sa.DateTime(timezone=True),nullable=True))
    if "scan_jobs" in tables and "probe_claim_token" not in columns:op.add_column("scan_jobs",sa.Column("probe_claim_token",sa.String(36),nullable=True))

def downgrade():
    tables=set(sa.inspect(op.get_bind()).get_table_names())
    for table in ("scan_schedules","scan_jobs"):
        if table not in tables:continue
        inspector=sa.inspect(op.get_bind());columns={x["name"] for x in inspector.get_columns(table)};indexes={x["name"] for x in inspector.get_indexes(table)}
        if f"ix_{table}_probe_id" in indexes:op.drop_index(f"ix_{table}_probe_id",table_name=table)
        with op.batch_alter_table(table) as batch:
            if table=="scan_jobs" and "probe_claim_token" in columns:batch.drop_column("probe_claim_token")
            if table=="scan_jobs" and "probe_claimed_at" in columns:batch.drop_column("probe_claimed_at")
            if "probe_id" in columns:batch.drop_column("probe_id")
    if "probes" in tables:op.drop_table("probes")
