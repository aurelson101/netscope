from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Asset, IpamAddress, IpamPrefix, TopologyLink, TopologyNode

INFRASTRUCTURE_TYPES={"firewall","router","switch","wireless access point","wireless controller"}


async def ensure_asset_node(db:AsyncSession,asset:Asset,address:str|None=None)->TopologyNode:
    node=(await db.execute(select(TopologyNode).where(TopologyNode.asset_id==asset.id))).scalar_one_or_none()
    label=asset.hostname or address or asset.id
    if not node:
        node=TopologyNode(asset_id=asset.id,label=label,kind=asset.device_type);db.add(node);await db.flush()
    else:node.label=label;node.kind=asset.device_type
    return node


async def rebuild_inferred_topology(db:AsyncSession)->int:
    created=0
    for prefix in (await db.execute(select(IpamPrefix))).scalars():
        addresses=(await db.execute(select(IpamAddress).where(IpamAddress.prefix_id==prefix.id,IpamAddress.asset_id.is_not(None)))).scalars().all()
        assets=[]
        for address in addresses:
            asset=await db.get(Asset,address.asset_id)
            if asset:assets.append((asset,address.address,await ensure_asset_node(db,asset,address.address)))
        if len(assets)<2:continue
        root=None
        if prefix.gateway:root=next((x for x in assets if x[1]==prefix.gateway),None)
        if not root:root=next((x for x in assets if x[0].device_type in INFRASTRUCTURE_TYPES),None)
        if not root:continue
        for asset,address,node in assets:
            if node.id==root[2].id:continue
            link=(await db.execute(select(TopologyLink).where(TopologyLink.source_node_id==root[2].id,TopologyLink.target_node_id==node.id,TopologyLink.source=="inferred_ipam"))).scalar_one_or_none()
            if not link:
                db.add(TopologyLink(source_node_id=root[2].id,target_node_id=node.id,source_port="LAN",target_port=address,source="inferred_ipam",confidence=0.6));created+=1
    await db.commit();return created
