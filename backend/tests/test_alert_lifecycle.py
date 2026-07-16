from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.models import Alert, Asset, AssetStatus, Base, Evidence, RawObservation
from app.services.alerts import evaluate_asset_lifecycle, open_alert, resolve_alert


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_lifecycle_ignores_manual_assets_and_alerts_observed_assets_once(db):
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=2)
    manual = Asset(hostname="manual", status=AssetStatus.online, last_seen=old)
    observed = Asset(hostname="observed", status=AssetStatus.online, last_seen=old)
    db.add_all([manual, observed]); await db.flush()
    observation = RawObservation(source="icmp", target="192.0.2.10", raw_data={})
    db.add(observation); await db.flush()
    db.add(Evidence(asset_id=observed.id,observation_id=observation.id,source="icmp",field="status",value="online",confidence=1.0))
    await db.commit()

    result = await evaluate_asset_lifecycle(db, now)
    assert result["offline"] == 1
    assert manual.status == AssetStatus.online
    assert observed.status == AssetStatus.offline
    assert await db.scalar(select(func.count()).select_from(Alert)) == 1

    result = await evaluate_asset_lifecycle(db, now + timedelta(minutes=5))
    assert result["offline"] == 0
    assert result["evaluated_offline"] == 1
    assert await db.scalar(select(func.count()).select_from(Alert)) == 1

    alert = await db.scalar(select(Alert))
    alert.status = "resolved"; alert.resolved_at = now
    await db.commit()
    await evaluate_asset_lifecycle(db, now + timedelta(minutes=10))
    assert alert.status == "open"


@pytest.mark.asyncio
async def test_resolved_alert_reopens_without_duplicate(db):
    await open_alert(db,fingerprint="asset_offline:1",kind="asset_offline",severity="critical",title="Offline",message="First")
    await db.commit()
    assert await resolve_alert(db,"asset_offline:1") is True
    await db.commit()

    reopened = await open_alert(db,fingerprint="asset_offline:1",kind="asset_offline",severity="critical",title="Offline",message="Again")
    await db.commit()
    assert reopened.status == "open"
    assert reopened.resolved_at is None
    assert reopened.message == "Again"
    assert await db.scalar(select(func.count()).select_from(Alert)) == 1
