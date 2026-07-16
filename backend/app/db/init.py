import ipaddress
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, func, select, update
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import Asset, AssetAddress, AuditLog, Base, DeviceRole, IpamAddress, IpamPrefix, Role, ScanJob, ScanProfile, Site, Subnet, User, UserSession
from app.services.vendors import infer_mobile_identity

async def recover_admin_access(db)->bool:
    if await db.scalar(select(func.count()).select_from(User).where(User.role==Role.admin,User.active.is_(True))):return False
    identifiers={settings.admin_identifier,settings.admin_username.strip().casefold()}
    recovery=(await db.execute(select(User).where(func.lower(User.username).in_(identifiers)).order_by(User.username))).scalars().first()
    if not recovery:return False
    desired_exists=await db.scalar(select(User.id).where(func.lower(User.username)==settings.admin_identifier,User.id!=recovery.id))
    if not desired_exists:recovery.username=settings.admin_identifier
    recovery.role=Role.admin;recovery.active=True
    db.add(AuditLog(user_id=recovery.id,action="admin_access_recovered",details={"reason":"no_active_administrator"}))
    return True


async def migrate_admin_identifier(db)->None:
    """Rename the legacy admin login without replacing its password or MFA."""
    desired=settings.admin_identifier
    if not desired or await db.scalar(select(User.id).where(func.lower(User.username)==desired)):return
    legacy=(await db.execute(select(User).where(func.lower(User.username)==settings.admin_username.strip().casefold(),User.role==Role.admin))).scalar_one_or_none()
    if not legacy:return
    previous=legacy.username
    legacy.username=desired
    db.add(AuditLog(user_id=legacy.id,action="admin_identifier_migrated",details={"previous":previous,"current":desired}))


async def init_db():
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await migrate_admin_identifier(db)
        retention=datetime.now(timezone.utc)-timedelta(days=30)
        await db.execute(delete(UserSession).where((UserSession.expires_at<retention)|((UserSession.revoked_at.is_not(None))&(UserSession.revoked_at<retention))))
        await db.execute(update(ScanJob).where(ScanJob.status.in_(["running","queued"])).values(status="failed",error="Scan interrompu par un redémarrage ou un worker indisponible"))
        await db.execute(update(Asset).where(Asset.manufacturer.ilike("%unknown%")).values(manufacturer=None))
        await db.execute(update(Asset).where(Asset.manufacturer.ilike("%locally administered%")).values(manufacturer=None))
        for asset in (await db.execute(select(Asset))).scalars():
            inferred=infer_mobile_identity(asset.hostname,asset.model,asset.operating_system)
            if inferred.get("manufacturer") and not asset.manufacturer:asset.manufacturer=inferred["manufacturer"]
            if inferred.get("operating_system") and not asset.operating_system:asset.operating_system=inferred["operating_system"]
            if inferred.get("device_type") and asset.device_type=="unknown":asset.device_type=inferred["device_type"]
            if inferred:asset.confidence=max(asset.confidence,0.68)
        if not await db.scalar(select(User.id).limit(1)):
            db.add(User(username=settings.admin_identifier,password_hash=hash_password(settings.admin_password),role=Role.admin))
        else:await recover_admin_access(db)
        if not await db.scalar(select(Site.id).limit(1)): db.add(Site(name="Principal",description="Site principal"))
        if not await db.scalar(select(ScanProfile.id).limit(1)):
            db.add_all([ScanProfile(name="Inventaire rapide",modules=["icmp","arp","nmap","dns"],options={"nmap":{"profile":"fast"}}),ScanProfile(name="Inventaire standard",modules=["icmp","arp","nmap","dns"],options={"nmap":{"profile":"standard"}}),ScanProfile(name="Découverte passive",modules=["dns"],options={})])
        if not await db.scalar(select(ScanProfile.id).where(ScanProfile.name == "Infrastructure SNMPv3")):
            db.add(ScanProfile(name="Infrastructure SNMPv3",modules=["nmap","snmp"],options={"nmap":{"profile":"fast"}}))
        if not await db.scalar(select(ScanProfile.id).where(ScanProfile.name == "Infrastructure SNMPv2c")):
            db.add(ScanProfile(name="Infrastructure SNMPv2c",modules=["nmap","snmp"],options={"nmap":{"profile":"fast"}}))
        if not await db.scalar(select(ScanProfile.id).where(ScanProfile.name == "Audit approfondi TCP")):
            db.add(ScanProfile(name="Audit approfondi TCP",modules=["nmap","dns"],options={"nmap":{"profile":"deep","max_rate":100}}))
        if not await db.scalar(select(ScanProfile.id).where(ScanProfile.name == "Services UDP essentiels")):
            db.add(ScanProfile(name="Services UDP essentiels",modules=["nmap","dns"],options={"nmap":{"profile":"udp","max_rate":50}}))
        if not await db.scalar(select(DeviceRole.id).limit(1)):
            db.add_all([DeviceRole(name="Poste utilisateur",slug="workstation",color="3b82f6"),DeviceRole(name="Serveur",slug="server",color="22c55e"),DeviceRole(name="Commutateur",slug="switch",color="8b5cf6"),DeviceRole(name="Routeur",slug="router",color="f59e0b"),DeviceRole(name="Pare-feu",slug="firewall",color="ef4444")])
        prefixes=(await db.execute(select(IpamPrefix))).scalars().all()
        for prefix in prefixes:
            if not await db.scalar(select(Subnet.id).where(Subnet.cidr==prefix.prefix)):
                db.add(Subnet(cidr=prefix.prefix,name=prefix.name,state="authorized",site_id=prefix.site_id))
        for found in (await db.execute(select(AssetAddress))).scalars():
            scope=IpamAddress.vrf_id.is_(None) if found.vrf_id is None else IpamAddress.vrf_id==found.vrf_id
            if await db.scalar(select(IpamAddress.id).where(IpamAddress.address==found.address,scope)):continue
            prefix=next((p for p in prefixes if p.vrf_id==found.vrf_id and ipaddress.ip_address(found.address) in ipaddress.ip_network(p.prefix)),None)
            if prefix:
                asset=await db.get(Asset,found.asset_id)
                db.add(IpamAddress(address=found.address,prefix_id=prefix.id,vrf_id=found.vrf_id,asset_id=found.asset_id,status="active",dns_name=asset.hostname if asset else None,source="discovery",last_seen=found.last_seen))
        await db.commit()
    async with SessionLocal() as db:
        from app.services.topology import rebuild_inferred_topology
        await rebuild_inferred_topology(db)
