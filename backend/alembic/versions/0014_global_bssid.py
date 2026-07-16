"""Treat a BSSID as one globally moving wireless identity."""
from alembic import op
import sqlalchemy as sa

revision="0014_global_bssid"
down_revision="0013_ipv6_routing_wifi"
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind();inspector=sa.inspect(bind);tables=set(inspector.get_table_names())
    if "wireless_networks" not in inspector.get_table_names():return
    if bind.dialect.name=="sqlite" and "assets" not in tables:
        indexes={x["name"] for x in inspector.get_indexes("wireless_networks")}
        if "uq_wireless_network_bssid_sparse" not in indexes:op.create_index("uq_wireless_network_bssid_sparse","wireless_networks",["bssid"],unique=True)
        return
    constraints={x.get("name") for x in inspector.get_unique_constraints("wireless_networks")}
    with op.batch_alter_table("wireless_networks") as batch:
        if "uq_wireless_network_radio_bssid" in constraints:batch.drop_constraint("uq_wireless_network_radio_bssid",type_="unique")
        if "uq_wireless_network_bssid" not in constraints:batch.create_unique_constraint("uq_wireless_network_bssid",["bssid"])

def downgrade():
    bind=op.get_bind();inspector=sa.inspect(bind);tables=set(inspector.get_table_names())
    if "wireless_networks" not in inspector.get_table_names():return
    if bind.dialect.name=="sqlite" and "assets" not in tables:
        if "uq_wireless_network_bssid_sparse" in {x["name"] for x in inspector.get_indexes("wireless_networks")}:op.drop_index("uq_wireless_network_bssid_sparse",table_name="wireless_networks")
        return
    constraints={x.get("name") for x in inspector.get_unique_constraints("wireless_networks")}
    with op.batch_alter_table("wireless_networks") as batch:
        if "uq_wireless_network_bssid" in constraints:batch.drop_constraint("uq_wireless_network_bssid",type_="unique")
        if "uq_wireless_network_radio_bssid" not in constraints:batch.create_unique_constraint("uq_wireless_network_radio_bssid",["radio_id","bssid"])
