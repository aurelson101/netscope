"""Add routing and wireless inventory with IPv6-capable addresses."""
from alembic import op
import sqlalchemy as sa

revision="0013_ipv6_routing_wifi"
down_revision="0012_interface_metrics"
branch_labels=None
depends_on=None

def upgrade():
    tables=set(sa.inspect(op.get_bind()).get_table_names())
    if "route_entries" not in tables:
        op.create_table("route_entries",sa.Column("id",sa.String(36),primary_key=True),sa.Column("network_device_id",sa.String(36),sa.ForeignKey("network_devices.id"),nullable=False),sa.Column("vrf_id",sa.String(36),sa.ForeignKey("vrfs.id"),nullable=True),sa.Column("prefix",sa.String(64),nullable=False),sa.Column("next_hop",sa.String(64),nullable=True),sa.Column("if_index",sa.Integer(),nullable=True),sa.Column("protocol",sa.String(30),nullable=False),sa.Column("metric",sa.Integer(),nullable=True),sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("last_seen",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("network_device_id","vrf_id","prefix","next_hop","protocol",name="uq_route_entry_identity"))
        op.create_index("ix_route_entries_network_device_id","route_entries",["network_device_id"]);op.create_index("ix_route_entries_vrf_id","route_entries",["vrf_id"]);op.create_index("ix_route_entries_prefix","route_entries",["prefix"])
    if "wireless_radios" not in tables:
        op.create_table("wireless_radios",sa.Column("id",sa.String(36),primary_key=True),sa.Column("asset_id",sa.String(36),sa.ForeignKey("assets.id"),nullable=False),sa.Column("radio_name",sa.String(120),nullable=False),sa.Column("band",sa.String(20),nullable=True),sa.Column("channel",sa.Integer(),nullable=True),sa.Column("channel_width_mhz",sa.Integer(),nullable=True),sa.Column("tx_power_dbm",sa.Float(),nullable=True),sa.Column("utilization",sa.Float(),nullable=True),sa.Column("noise_dbm",sa.Float(),nullable=True),sa.Column("client_count",sa.Integer(),nullable=False,server_default="0"),sa.Column("last_seen",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("asset_id","radio_name",name="uq_wireless_radio_asset_name"));op.create_index("ix_wireless_radios_asset_id","wireless_radios",["asset_id"])
    if "wireless_networks" not in tables:
        op.create_table("wireless_networks",sa.Column("id",sa.String(36),primary_key=True),sa.Column("radio_id",sa.String(36),sa.ForeignKey("wireless_radios.id"),nullable=False),sa.Column("ssid",sa.String(255),nullable=False),sa.Column("bssid",sa.String(32),nullable=False),sa.Column("security",sa.String(40),nullable=True),sa.Column("vlan_id",sa.Integer(),nullable=True),sa.Column("hidden",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("client_count",sa.Integer(),nullable=False,server_default="0"),sa.Column("last_seen",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("radio_id","bssid",name="uq_wireless_network_radio_bssid"));op.create_index("ix_wireless_networks_radio_id","wireless_networks",["radio_id"]);op.create_index("ix_wireless_networks_ssid","wireless_networks",["ssid"]);op.create_index("ix_wireless_networks_bssid","wireless_networks",["bssid"])

def downgrade():
    tables=set(sa.inspect(op.get_bind()).get_table_names())
    for table in ("wireless_networks","wireless_radios","route_entries"):
        if table in tables:op.drop_table(table)
