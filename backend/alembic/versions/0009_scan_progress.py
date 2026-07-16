"""Expose scan progress and discovered result counts."""
from alembic import op
import sqlalchemy as sa

revision="0009_scan_progress"
down_revision="0008_identity_binding_vrf"
branch_labels=None
depends_on=None

def upgrade():
    inspector=sa.inspect(op.get_bind())
    if "scan_jobs" not in inspector.get_table_names():return
    columns={x["name"] for x in inspector.get_columns("scan_jobs")}
    additions=(("progress",sa.Column("progress",sa.Integer(),nullable=False,server_default="0")),("current_module",sa.Column("current_module",sa.String(30),nullable=True)),("result_count",sa.Column("result_count",sa.Integer(),nullable=False,server_default="0")))
    for name,column in additions:
        if name not in columns:op.add_column("scan_jobs",column)

def downgrade():
    inspector=sa.inspect(op.get_bind())
    if "scan_jobs" not in inspector.get_table_names():return
    columns={x["name"] for x in inspector.get_columns("scan_jobs")}
    with op.batch_alter_table("scan_jobs") as batch:
        for name in ("result_count","current_module","progress"):
            if name in columns:batch.drop_column(name)
