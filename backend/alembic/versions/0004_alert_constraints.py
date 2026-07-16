"""Ensure alert constraints on databases upgraded during development."""
from alembic import op
import sqlalchemy as sa

revision="0004_alert_constraints"
down_revision="0003_alerts"
branch_labels=None
depends_on=None

CONSTRAINTS={
    "ck_alerts_severity":"severity IN ('info','warning','critical')",
    "ck_alerts_status":"status IN ('open','acknowledged','resolved')",
}

def upgrade():
    bind=op.get_bind();inspector=sa.inspect(bind)
    if "alerts" not in inspector.get_table_names():return
    existing={item.get("name") for item in inspector.get_check_constraints("alerts")}
    missing={name:expression for name,expression in CONSTRAINTS.items() if name not in existing}
    if not missing:return
    if bind.dialect.name=="sqlite":
        with op.batch_alter_table("alerts") as batch:
            for name,expression in missing.items():batch.create_check_constraint(name,expression)
    else:
        for name,expression in missing.items():op.create_check_constraint(name,"alerts",expression)

def downgrade():
    bind=op.get_bind();inspector=sa.inspect(bind)
    if "alerts" not in inspector.get_table_names():return
    existing={item.get("name") for item in inspector.get_check_constraints("alerts")}
    targets=[name for name in CONSTRAINTS if name in existing]
    if bind.dialect.name=="sqlite":
        with op.batch_alter_table("alerts") as batch:
            for name in targets:batch.drop_constraint(name,type_="check")
    else:
        for name in targets:op.drop_constraint(name,"alerts",type_="check")
