"""Add persistent operational alerts."""
from alembic import op
import sqlalchemy as sa

revision="0003_alerts"
down_revision="0002_ipam_hierarchy"
branch_labels=None
depends_on=None

def upgrade():
    if "alerts" in sa.inspect(op.get_bind()).get_table_names():return
    op.create_table("alerts",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("fingerprint",sa.String(255),nullable=False),
        sa.Column("kind",sa.String(80),nullable=False),
        sa.Column("severity",sa.String(20),nullable=False,server_default="warning"),
        sa.Column("status",sa.String(20),nullable=False,server_default="open"),
        sa.Column("title",sa.String(255),nullable=False),
        sa.Column("message",sa.Text(),nullable=False),
        sa.Column("asset_id",sa.String(36),sa.ForeignKey("assets.id")),
        sa.Column("details",sa.JSON(),nullable=False),
        sa.Column("first_seen",sa.DateTime(timezone=True),nullable=False),
        sa.Column("last_seen",sa.DateTime(timezone=True),nullable=False),
        sa.Column("acknowledged_at",sa.DateTime(timezone=True)),
        sa.Column("acknowledged_by",sa.String(36),sa.ForeignKey("users.id")),
        sa.Column("resolved_at",sa.DateTime(timezone=True)),
        sa.CheckConstraint("severity IN ('info','warning','critical')",name="ck_alerts_severity"),
        sa.CheckConstraint("status IN ('open','acknowledged','resolved')",name="ck_alerts_status"))
    for column in ("fingerprint","kind","severity","status","asset_id"):op.create_index(f"ix_alerts_{column}","alerts",[column],unique=column=="fingerprint")

def downgrade():
    if "alerts" in sa.inspect(op.get_bind()).get_table_names():op.drop_table("alerts")
