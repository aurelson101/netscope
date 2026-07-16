"""Add SSH vault metadata and encrypted network configuration versions."""
from alembic import op
import sqlalchemy as sa

revision="0015_device_configs"
down_revision="0014_global_bssid"
branch_labels=None
depends_on=None

def upgrade():
    inspector=sa.inspect(op.get_bind());tables=set(inspector.get_table_names())
    if "credentials" in tables:
        columns={x["name"] for x in inspector.get_columns("credentials")}
        for name,column in (("description",sa.Column("description",sa.String(255),nullable=True)),("last_used_at",sa.Column("last_used_at",sa.DateTime(timezone=True),nullable=True)),("updated_at",sa.Column("updated_at",sa.DateTime(timezone=True),nullable=True))):
            if name not in columns:op.add_column("credentials",column)
        op.execute("UPDATE credentials SET updated_at=created_at WHERE updated_at IS NULL")
    if "device_configurations" not in tables:
        op.create_table("device_configurations",sa.Column("id",sa.String(36),primary_key=True),sa.Column("asset_id",sa.String(36),sa.ForeignKey("assets.id"),nullable=False),sa.Column("credential_id",sa.String(36),sa.ForeignKey("credentials.id"),nullable=True),sa.Column("platform",sa.String(30),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("encrypted_content",sa.Text(),nullable=True),sa.Column("checksum",sa.String(64),nullable=True),sa.Column("byte_count",sa.Integer(),nullable=True),sa.Column("error",sa.Text(),nullable=True),sa.Column("created_by",sa.String(36),sa.ForeignKey("users.id"),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("captured_at",sa.DateTime(timezone=True),nullable=True));op.create_index("ix_device_configurations_asset_id","device_configurations",["asset_id"]);op.create_index("ix_device_configurations_status","device_configurations",["status"])
    if "device_configuration_restores" not in tables:
        op.create_table("device_configuration_restores",sa.Column("id",sa.String(36),primary_key=True),sa.Column("configuration_id",sa.String(36),sa.ForeignKey("device_configurations.id"),nullable=False),sa.Column("pre_backup_id",sa.String(36),sa.ForeignKey("device_configurations.id"),nullable=True),sa.Column("status",sa.String(20),nullable=False),sa.Column("error",sa.Text(),nullable=True),sa.Column("requested_by",sa.String(36),sa.ForeignKey("users.id"),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("started_at",sa.DateTime(timezone=True),nullable=True),sa.Column("finished_at",sa.DateTime(timezone=True),nullable=True));op.create_index("ix_device_configuration_restores_configuration_id","device_configuration_restores",["configuration_id"]);op.create_index("ix_device_configuration_restores_status","device_configuration_restores",["status"])

def downgrade():
    inspector=sa.inspect(op.get_bind());tables=set(inspector.get_table_names())
    if "device_configuration_restores" in tables:op.drop_table("device_configuration_restores")
    if "device_configurations" in tables:op.drop_table("device_configurations")
    if "credentials" in tables:
        columns={x["name"] for x in inspector.get_columns("credentials")}
        with op.batch_alter_table("credentials") as batch:
            for name in ("updated_at","last_used_at","description"):
                if name in columns:batch.drop_column(name)
