"""Scope IPAM addresses, prefixes and scans by VRF."""
from alembic import op
import sqlalchemy as sa

revision="0006_multi_vrf"
down_revision="0005_identity_bindings"
branch_labels=None
depends_on=None

def _drop_unique(table,columns):
    inspector=sa.inspect(op.get_bind())
    for constraint in inspector.get_unique_constraints(table):
        if set(constraint.get("column_names") or [])==set(columns):
            with op.batch_alter_table(table) as batch:batch.drop_constraint(constraint["name"],type_="unique")
    for index in inspector.get_indexes(table):
        if index.get("unique") and set(index.get("column_names") or [])==set(columns):op.drop_index(index["name"],table_name=table)

def _create_index(name,table,columns,**kwargs):
    if name not in {x["name"] for x in sa.inspect(op.get_bind()).get_indexes(table)}:op.create_index(name,table,columns,**kwargs)

def upgrade():
    inspector=sa.inspect(op.get_bind());tables=set(inspector.get_table_names())
    additions={
        "asset_addresses":("vrf_id",),
        "ipam_addresses":("vrf_id",),
        "scan_jobs":("vrf_id",),
        "scan_schedules":("vrf_id",),
    }
    for table in additions:
        if table not in tables:continue
        columns={x["name"] for x in inspector.get_columns(table)}
        if "vrf_id" not in columns:
            with op.batch_alter_table(table) as batch:batch.add_column(sa.Column("vrf_id",sa.String(36),nullable=True))
    if {"ipam_addresses","ipam_prefixes"}<=tables:op.execute("UPDATE ipam_addresses SET vrf_id=(SELECT vrf_id FROM ipam_prefixes WHERE ipam_prefixes.id=ipam_addresses.prefix_id) WHERE prefix_id IS NOT NULL")
    if "ipam_prefixes" in tables:_drop_unique("ipam_prefixes",["prefix"])
    if "ipam_addresses" in tables:_drop_unique("ipam_addresses",["address"])
    if "asset_addresses" in tables:_drop_unique("asset_addresses",["asset_id","address"])
    # Foreign keys are intentionally added after data backfill.
    for table in additions:
        if table not in tables:continue
        foreign_keys={fk.get("name") for fk in sa.inspect(op.get_bind()).get_foreign_keys(table)}
        if f"fk_{table}_vrf_id" not in foreign_keys and not any(fk.get("constrained_columns")==["vrf_id"] for fk in sa.inspect(op.get_bind()).get_foreign_keys(table)):
            with op.batch_alter_table(table) as batch:batch.create_foreign_key(f"fk_{table}_vrf_id","vrfs",["vrf_id"],["id"])
        _create_index(f"ix_{table}_vrf_id",table,["vrf_id"])
    if "ipam_prefixes" in tables:
        _create_index("uq_ipam_prefixes_global","ipam_prefixes",["prefix"],unique=True,postgresql_where=sa.text("vrf_id IS NULL"),sqlite_where=sa.text("vrf_id IS NULL"));_create_index("uq_ipam_prefixes_vrf","ipam_prefixes",["prefix","vrf_id"],unique=True,postgresql_where=sa.text("vrf_id IS NOT NULL"),sqlite_where=sa.text("vrf_id IS NOT NULL"))
    if "ipam_addresses" in tables:
        _create_index("uq_ipam_addresses_global","ipam_addresses",["address"],unique=True,postgresql_where=sa.text("vrf_id IS NULL"),sqlite_where=sa.text("vrf_id IS NULL"));_create_index("uq_ipam_addresses_vrf","ipam_addresses",["address","vrf_id"],unique=True,postgresql_where=sa.text("vrf_id IS NOT NULL"),sqlite_where=sa.text("vrf_id IS NOT NULL"))
    if "asset_addresses" in tables:
        _create_index("uq_asset_addresses_global","asset_addresses",["asset_id","address"],unique=True,postgresql_where=sa.text("vrf_id IS NULL"),sqlite_where=sa.text("vrf_id IS NULL"));_create_index("uq_asset_addresses_vrf","asset_addresses",["asset_id","address","vrf_id"],unique=True,postgresql_where=sa.text("vrf_id IS NOT NULL"),sqlite_where=sa.text("vrf_id IS NOT NULL"))

def downgrade():
    # Downgrade is refused when duplicate values across VRFs cannot fit the legacy global uniqueness model.
    bind=op.get_bind()
    tables=set(sa.inspect(bind).get_table_names())
    for table,column in (("ipam_prefixes","prefix"),("ipam_addresses","address")):
        if table not in tables:continue
        duplicate=bind.execute(sa.text(f"SELECT {column} FROM {table} GROUP BY {column} HAVING COUNT(*)>1 LIMIT 1")).first()
        if duplicate:raise RuntimeError(f"Impossible de revenir au schéma global: doublon {table}.{column}={duplicate[0]}")
    for name,table in (("uq_ipam_prefixes_global","ipam_prefixes"),("uq_ipam_prefixes_vrf","ipam_prefixes"),("uq_ipam_addresses_global","ipam_addresses"),("uq_ipam_addresses_vrf","ipam_addresses"),("uq_asset_addresses_global","asset_addresses"),("uq_asset_addresses_vrf","asset_addresses")):
        if table in tables and name in {x["name"] for x in sa.inspect(bind).get_indexes(table)}:op.drop_index(name,table_name=table)
    if "ipam_prefixes" in tables:_drop_unique("ipam_prefixes",["prefix"])
    if "ipam_addresses" in tables:_drop_unique("ipam_addresses",["address"])
    if "asset_addresses" in tables:_drop_unique("asset_addresses",["asset_id","address"])
    if "ipam_prefixes" in tables:
        with op.batch_alter_table("ipam_prefixes") as batch:batch.create_unique_constraint("uq_ipam_prefixes_prefix",["prefix"])
    if "ipam_addresses" in tables:
        with op.batch_alter_table("ipam_addresses") as batch:batch.create_unique_constraint("uq_ipam_addresses_address",["address"])
    if "asset_addresses" in tables:
        with op.batch_alter_table("asset_addresses") as batch:batch.create_unique_constraint("uq_asset_addresses_asset_address",["asset_id","address"])
    for table in ("asset_addresses","ipam_addresses","scan_jobs","scan_schedules"):
        if table not in tables or "vrf_id" not in {x["name"] for x in sa.inspect(bind).get_columns(table)}:continue
        index_name=f"ix_{table}_vrf_id"
        if index_name in {x["name"] for x in sa.inspect(bind).get_indexes(table)}:op.drop_index(index_name,table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_column("vrf_id")
