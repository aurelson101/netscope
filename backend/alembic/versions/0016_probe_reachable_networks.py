"""store routes reported by distributed probes"""
from alembic import op
import sqlalchemy as sa

revision="0016_probe_reachable_networks"
down_revision="0015_device_configs"
branch_labels=None
depends_on=None

def upgrade():
    columns={column["name"] for column in sa.inspect(op.get_bind()).get_columns("probes")}
    if "reachable_networks" not in columns:
        op.add_column("probes",sa.Column("reachable_networks",sa.JSON(),nullable=False,server_default=sa.text("'[]'")))

def downgrade():
    columns={column["name"] for column in sa.inspect(op.get_bind()).get_columns("probes")}
    if "reachable_networks" in columns:op.drop_column("probes","reachable_networks")
