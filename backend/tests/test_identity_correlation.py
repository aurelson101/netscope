import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.correlation.engine import correlate
from app.discovery.base import DiscoveryResult
from app.models import Alert, Asset, AssetAddress, AssetIdentifier, Base, IpamAddress, NetworkIdentityBinding
from app.services.identity import resolve_identity


@pytest_asyncio.fixture
async def db():
    engine=create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async with factory() as session:yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_mac_identity_wins_and_conflict_is_not_silently_reassigned(db):
    hardware=Asset(hostname="hardware");previous=Asset(hostname="previous")
    db.add_all([hardware,previous]);await db.flush()
    db.add(AssetIdentifier(asset_id=hardware.id,kind="mac",value="00:11:22:33:44:55",confidence=1))
    db.add(AssetAddress(asset_id=previous.id,address="192.0.2.10",version=4))
    ipam=IpamAddress(address="192.0.2.10",asset_id=previous.id,status="active",source="discovery")
    db.add(ipam);await db.commit()

    resolution=await resolve_identity(db,"192.0.2.10","00:11:22:33:44:55")
    assert resolution.asset.id==hardware.id
    assert resolution.conflict is True

    result=DiscoveryResult("arp","192.0.2.10",{},[
        {"field":"ip","value":"192.0.2.10","confidence":1},
        {"field":"mac","value":"00:11:22:33:44:55","confidence":1},
        {"field":"status","value":"online","confidence":1},
    ])
    asset=await correlate(db,result)
    assert asset.id==hardware.id
    assert ipam.asset_id==previous.id
    assert not await db.scalar(select(AssetAddress.id).where(AssetAddress.asset_id==hardware.id,AssetAddress.address=="192.0.2.10"))
    alert=await db.scalar(select(Alert).where(Alert.kind=="ip_mac_conflict"))
    assert alert and alert.severity=="critical"
    binding=await db.scalar(select(NetworkIdentityBinding).where(NetworkIdentityBinding.asset_id==hardware.id))
    assert binding and binding.ip_address=="192.0.2.10" and binding.vrf_id is None


@pytest.mark.asyncio
async def test_ip_only_observation_reuses_asset_without_conflict(db):
    asset=Asset(hostname="known");db.add(asset);await db.flush()
    db.add(AssetAddress(asset_id=asset.id,address="198.51.100.4",version=4));await db.commit()
    resolution=await resolve_identity(db,"198.51.100.4",None)
    assert resolution.asset.id==asset.id and not resolution.conflict
