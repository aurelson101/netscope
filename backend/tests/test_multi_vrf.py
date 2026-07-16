import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.models import Base, IpamAddress, IpamPrefix, Vrf


@pytest_asyncio.fixture
async def db():
    engine=create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async with factory() as session:yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_same_prefix_and_address_are_allowed_in_distinct_vrfs(db):
    blue=Vrf(name="blue",route_distinguisher="65000:1");red=Vrf(name="red",route_distinguisher="65000:2")
    db.add_all([blue,red]);await db.flush()
    p1=IpamPrefix(prefix="10.0.0.0/24",name="blue",vrf_id=blue.id)
    p2=IpamPrefix(prefix="10.0.0.0/24",name="red",vrf_id=red.id)
    db.add_all([p1,p2]);await db.flush()
    db.add_all([IpamAddress(address="10.0.0.10",prefix_id=p1.id,vrf_id=blue.id),IpamAddress(address="10.0.0.10",prefix_id=p2.id,vrf_id=red.id)])
    await db.commit()


@pytest.mark.asyncio
async def test_duplicate_address_in_same_vrf_is_rejected(db):
    vrf=Vrf(name="tenant",route_distinguisher="65000:10");db.add(vrf);await db.flush()
    db.add_all([IpamAddress(address="192.0.2.5",vrf_id=vrf.id),IpamAddress(address="192.0.2.5",vrf_id=vrf.id)])
    with pytest.raises(IntegrityError):await db.commit()
