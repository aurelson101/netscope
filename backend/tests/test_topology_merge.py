import pytest
import pytest_asyncio
from sqlalchemy import func,select
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from app.models import Asset,Base,TopologyNode
from app.services.topology import ensure_asset_node

@pytest_asyncio.fixture
async def db():
    engine=create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async with factory() as session:yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_discovered_asset_claims_existing_lldp_placeholder(db):
    placeholder=TopologyNode(label="switch-edge",kind="network");asset=Asset(hostname="SWITCH-EDGE",device_type="switch");db.add_all([placeholder,asset]);await db.commit()
    node=await ensure_asset_node(db,asset)
    assert node.id==placeholder.id and node.asset_id==asset.id
    assert await db.scalar(select(func.count()).select_from(TopologyNode))==1
