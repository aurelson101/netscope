from datetime import datetime,timedelta,timezone
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from app.models import Alert,Base,Probe
from app.services.probes import evaluate_probe_health

@pytest_asyncio.fixture
async def db():
    engine=create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async with factory() as session:yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_offline_probe_opens_alert(db):
    probe=Probe(name="Remote",token_hash="x",capabilities=[],created_at=datetime.now(timezone.utc)-timedelta(minutes=10));db.add(probe);await db.commit()
    assert await evaluate_probe_health(db)==1
    alert=(await db.execute(select(Alert).where(Alert.fingerprint==f"probe_offline:{probe.id}"))).scalar_one()
    assert alert.severity=="critical"
