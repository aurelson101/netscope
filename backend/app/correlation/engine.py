from datetime import datetime, timezone
import ipaddress
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.discovery.base import DiscoveryResult
from app.models import Asset, AssetAddress, AssetArchive, AssetHistory, AssetIdentifier, AssetMetadata, AssetService, AssetStatus, Evidence, IpamAddress, IpamPrefix, RawObservation
from app.services.vendors import infer_mobile_identity,normalize_mac,normalize_vendor,vendor_from_mac
from app.services.alerts import open_alert,resolve_alert


NORMAL_VENDOR={"CISCO SYSTEMS, INC.":"Cisco","CISCO SYSTEMS":"Cisco","HP INC.":"HP Inc.","HEWLETT PACKARD ENTERPRISE":"HPE","UBIQUITI NETWORKS":"Ubiquiti"}
UNKNOWN_VENDORS=("UNKNOWN","LOCALLY ADMINISTERED","PRIVATE","RANDOMIZED")


async def correlate(db: AsyncSession, result: DiscoveryResult, scan_id: str | None = None) -> Asset:
    observation=RawObservation(scan_id=scan_id,source=result.source,target=result.target,raw_data=result.raw); db.add(observation); await db.flush()
    facts={f["field"]:f for f in result.facts if f["field"] != "service"}
    mac=normalize_mac(facts.get("mac",{}).get("value"));ip=facts.get("ip",{}).get("value",result.target)
    asset=None
    if mac:
        asset=(await db.execute(select(Asset).join(AssetIdentifier).where(AssetIdentifier.kind=="mac",AssetIdentifier.value==mac))).scalar_one_or_none()
    if not asset:
        asset=(await db.execute(select(Asset).join(AssetAddress).where(AssetAddress.address==ip))).scalar_one_or_none()
    created=asset is None
    if created:
        asset=Asset(status=AssetStatus.unknown); db.add(asset); await db.flush(); db.add(AssetHistory(asset_id=asset.id,event_type="asset_created",new_value=ip))
        await open_alert(db,fingerprint=f"new_asset:{asset.id}",kind="new_asset",severity="info",title="Nouvel équipement découvert",message=f"Un nouvel équipement a été découvert à l'adresse {ip}.",asset_id=asset.id,details={"address":ip,"source":result.source})
    archive=await db.get(AssetArchive,asset.id)
    if archive:
        await db.delete(archive)
        db.add(AssetHistory(asset_id=asset.id,event_type="asset_restored_by_discovery",old_value=archive.reason,new_value=result.source))
    address=(await db.execute(select(AssetAddress).where(AssetAddress.asset_id==asset.id,AssetAddress.address==ip))).scalar_one_or_none()
    if not address: db.add(AssetAddress(asset_id=asset.id,address=ip,version=6 if ":" in ip else 4))
    ipam=(await db.execute(select(IpamAddress).where(IpamAddress.address==ip))).scalar_one_or_none()
    if not ipam:
        prefix_id=None
        for prefix in (await db.execute(select(IpamPrefix))).scalars():
            if ipaddress.ip_address(ip) in ipaddress.ip_network(prefix.prefix):prefix_id=prefix.id;break
        db.add(IpamAddress(address=ip,prefix_id=prefix_id,asset_id=asset.id,status="active",dns_name=facts.get("hostname",{}).get("value"),source="discovery",last_seen=datetime.now(timezone.utc)))
    else:
        ipam.asset_id=asset.id;ipam.last_seen=datetime.now(timezone.utc);ipam.status="active"
    if mac:
        identifier=(await db.execute(select(AssetIdentifier).where(AssetIdentifier.asset_id==asset.id,AssetIdentifier.kind=="mac",AssetIdentifier.value==mac))).scalar_one_or_none()
        if not identifier: db.add(AssetIdentifier(asset_id=asset.id,kind="mac",value=mac,confidence=1))
        if "manufacturer" not in facts:
            oui_vendor=vendor_from_mac(mac)
            if oui_vendor:facts["manufacturer"]={"field":"manufacturer","value":oui_vendor,"confidence":0.85}
    mapping={"hostname":"hostname","manufacturer":"manufacturer","model":"model","device_type":"device_type","operating_system":"operating_system"}
    metadata=await db.get(AssetMetadata,asset.id)
    locked=set((metadata.custom_fields or {}).get("_locked_identity_fields",[])) if metadata else set()
    for field, attr in mapping.items():
        if field in locked:continue
        if field in facts:
            value=facts[field]["value"]
            if field=="manufacturer": value=normalize_vendor(NORMAL_VENDOR.get(value.upper(),value))
            if field=="manufacturer" and any(marker in value.upper() for marker in UNKNOWN_VENDORS):
                continue
            old=getattr(asset,attr)
            if value and old != value:
                setattr(asset,attr,value); db.add(AssetHistory(asset_id=asset.id,event_type=f"{field}_changed",old_value=old,new_value=str(value)))
    inferred=infer_mobile_identity(asset.hostname,asset.model,asset.operating_system)
    for field,value in inferred.items():
        if field not in locked and (not getattr(asset,field) or getattr(asset,field)=="unknown"):
            old=getattr(asset,field);setattr(asset,field,value);db.add(AssetHistory(asset_id=asset.id,event_type=f"{field}_inferred",old_value=old,new_value=value))
            asset.confidence=max(asset.confidence,0.68)
    if facts.get("status",{}).get("value") in ("up","online"):
        if asset.status!=AssetStatus.online:db.add(AssetHistory(asset_id=asset.id,event_type="status_changed",old_value=asset.status.value,new_value=AssetStatus.online.value))
        asset.status=AssetStatus.online
        await resolve_alert(db,f"asset_offline:{asset.id}")
    asset.last_seen=datetime.now(timezone.utc); asset.confidence=max(asset.confidence,max([float(f.get("confidence",0)) for f in result.facts] or [0]))
    for fact in result.facts:
        value=fact["value"]
        db.add(Evidence(asset_id=asset.id,observation_id=observation.id,source=result.source,field=fact["field"],value=str(value),confidence=float(fact.get("confidence",0))))
        if fact["field"]=="service":
            s=value
            existing=await db.scalar(select(AssetService.id).where(AssetService.asset_id==asset.id,AssetService.protocol==s["protocol"],AssetService.port==s["port"]))
            if not existing: db.add(AssetService(asset_id=asset.id,**s))
    ports={int(f["value"]["port"]) for f in result.facts if f["field"]=="service"}
    if 445 in ports or 3389 in ports:
        if not asset.operating_system: asset.operating_system="Windows (probable)"
        if asset.device_type=="unknown": asset.device_type="workstation"
        asset.confidence=max(asset.confidence,0.72)
    await db.commit()
    if result.source == "snmp":
        from app.services.infrastructure import ingest_infrastructure
        await ingest_infrastructure(db, asset, ip, result.raw.get("sections", {}))
    return asset
