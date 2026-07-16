from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Asset, AssetAddress, AssetIdentifier


@dataclass
class IdentityResolution:
    asset: Asset | None
    mac_asset: Asset | None
    ip_asset: Asset | None
    conflict: bool


async def resolve_identity(db: AsyncSession, ip: str, mac: str | None, vrf_id: str | None = None) -> IdentityResolution:
    mac_asset = None
    if mac:
        mac_asset = await db.scalar(select(Asset).join(AssetIdentifier).where(AssetIdentifier.kind == "mac",AssetIdentifier.value == mac))
    scope=AssetAddress.vrf_id.is_(None) if vrf_id is None else AssetAddress.vrf_id==vrf_id
    ip_asset = await db.scalar(select(Asset).join(AssetAddress).where(AssetAddress.address == ip,scope).order_by(Asset.last_seen.desc()))
    conflict = bool(mac_asset and ip_asset and mac_asset.id != ip_asset.id)
    # A hardware identifier wins over an address that may have been reassigned by DHCP.
    return IdentityResolution(asset=mac_asset or (None if mac else ip_asset),mac_asset=mac_asset,ip_asset=ip_asset,conflict=conflict)
