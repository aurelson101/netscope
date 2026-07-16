"""Persist SNMP interface counters and calculated utilization."""
from alembic import op
import sqlalchemy as sa

revision="0012_interface_metrics"
down_revision="0011_distributed_probes"
branch_labels=None
depends_on=None

def upgrade():
    inspector=sa.inspect(op.get_bind());tables=set(inspector.get_table_names())
    if "topology_links" in tables:
        old=next((x for x in inspector.get_unique_constraints("topology_links") if x.get("column_names")==["source_node_id","target_node_id","source"]),None)
        if old and old.get("name"):
            with op.batch_alter_table("topology_links") as batch:batch.drop_constraint(old["name"],type_="unique");batch.create_unique_constraint("uq_topology_link_ports",["source_node_id","target_node_id","source","source_port","target_port"])
    if "interface_metrics" in tables or "switch_ports" not in tables:return
    op.create_table("interface_metrics",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("switch_port_id",sa.String(36),sa.ForeignKey("switch_ports.id"),nullable=False),sa.Column("collected_at",sa.DateTime(timezone=True),nullable=False),sa.Column("speed_bps",sa.BigInteger(),nullable=True),sa.Column("in_octets",sa.BigInteger(),nullable=True),sa.Column("out_octets",sa.BigInteger(),nullable=True),sa.Column("in_errors",sa.BigInteger(),nullable=True),sa.Column("out_errors",sa.BigInteger(),nullable=True),sa.Column("in_bps",sa.Float(),nullable=True),sa.Column("out_bps",sa.Float(),nullable=True),sa.Column("in_utilization",sa.Float(),nullable=True),sa.Column("out_utilization",sa.Float(),nullable=True))
    op.create_index("ix_interface_metrics_switch_port_id","interface_metrics",["switch_port_id"]);op.create_index("ix_interface_metrics_port_time","interface_metrics",["switch_port_id","collected_at"])

def downgrade():
    inspector=sa.inspect(op.get_bind());tables=set(inspector.get_table_names())
    if "interface_metrics" in tables:op.drop_table("interface_metrics")
    if "topology_links" in tables:
        constraints={x.get("name") for x in inspector.get_unique_constraints("topology_links")}
        if "uq_topology_link_ports" in constraints:
            with op.batch_alter_table("topology_links") as batch:batch.drop_constraint("uq_topology_link_ports",type_="unique");batch.create_unique_constraint("uq_topology_links_nodes_source",["source_node_id","target_node_id","source"])
