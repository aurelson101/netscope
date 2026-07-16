"""Attach identity observations to their VRF context."""
from alembic import op
import sqlalchemy as sa

revision="0008_identity_binding_vrf"
down_revision="0007_legacy_ip_indexes"
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind();inspector=sa.inspect(bind);tables=set(inspector.get_table_names())
    if "network_identity_bindings" not in inspector.get_table_names():return
    if "vrf_id" not in {x["name"] for x in inspector.get_columns("network_identity_bindings")}:
        op.add_column("network_identity_bindings",sa.Column("vrf_id",sa.String(36),nullable=True))
        if bind.dialect.name!="sqlite" and "vrfs" in tables:op.create_foreign_key("fk_identity_bindings_vrf_id","network_identity_bindings","vrfs",["vrf_id"],["id"])
        op.create_index("ix_network_identity_bindings_vrf_id","network_identity_bindings",["vrf_id"])

def downgrade():
    bind=op.get_bind();inspector=sa.inspect(bind);tables=set(inspector.get_table_names())
    if "network_identity_bindings" not in inspector.get_table_names() or "vrf_id" not in {x["name"] for x in inspector.get_columns("network_identity_bindings")}:return
    if "ix_network_identity_bindings_vrf_id" in {x["name"] for x in inspector.get_indexes("network_identity_bindings")}:op.drop_index("ix_network_identity_bindings_vrf_id",table_name="network_identity_bindings")
    if bind.dialect.name=="sqlite" and not {"assets","vrfs"}<=tables:op.drop_column("network_identity_bindings","vrf_id")
    else:
        with op.batch_alter_table("network_identity_bindings") as batch:batch.drop_column("vrf_id")
