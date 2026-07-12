import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from app.core.config import settings
from app.db.init import recover_admin_access
from app.models import AuditLog,Base,Role,User

@pytest.mark.asyncio
async def test_recovers_configured_account_when_no_admin_exists(tmp_path):
    engine=create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'admin.db'}")
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with sessions() as db:
        account=User(username=settings.admin_username,password_hash="unused",role=Role.operator,active=True);db.add(account);await db.commit()
        assert await recover_admin_access(db);await db.commit()
        assert account.role==Role.admin
        assert await db.scalar(select(AuditLog.id).where(AuditLog.action=="admin_access_recovered"))
    await engine.dispose()
