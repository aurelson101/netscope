"""Remove legacy global unique indexes left by early schemas."""
from alembic import op
import sqlalchemy as sa

revision="0007_legacy_ip_indexes"
down_revision="0006_multi_vrf"
branch_labels=None
depends_on=None

LEGACY={"ipam_prefixes":("prefix",),"ipam_addresses":("address",)}

def upgrade():
    inspector=sa.inspect(op.get_bind());tables=set(inspector.get_table_names())
    for table,columns in LEGACY.items():
        if table not in tables:continue
        for index in inspector.get_indexes(table):
            if index["name"].startswith("uq_ipam_"):continue
            if index.get("unique") and tuple(index.get("column_names") or ())==columns:op.drop_index(index["name"],table_name=table)

def downgrade():
    bind=op.get_bind();inspector=sa.inspect(bind);tables=set(inspector.get_table_names())
    for table,columns in LEGACY.items():
        if table not in tables:continue
        duplicate=bind.execute(sa.text(f"SELECT {columns[0]} FROM {table} GROUP BY {columns[0]} HAVING COUNT(*)>1 LIMIT 1")).first()
        if duplicate:raise RuntimeError(f"Impossible de restaurer l'index global: doublon {table}.{columns[0]}={duplicate[0]}")
        name=f"ix_{table}_{columns[0]}"
        if name in {x["name"] for x in sa.inspect(bind).get_indexes(table)}:op.drop_index(name,table_name=table)
        op.create_index(name,table,list(columns),unique=True)
