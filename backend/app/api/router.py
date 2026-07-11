import asyncio
import csv
import io
import ipaddress
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
import pyotp
import dns.reversename
import dns.resolver
import time
import smtplib
from email.message import EmailMessage
import re
import json
import redis.asyncio as redis
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.security import create_token, current_user, hash_password, require, verify_password
from app.core.config import settings
from app.db.session import get_db
from app.models import Asset, AssetAddress, AssetArchive, AssetHistory, AssetIdentifier, AssetMetadata, AssetService, AssetStatus, AuditLog, Credential, DeviceRole, Evidence, IpamAddress, IpamPrefix, NetworkDevice, PortMacEntry, RawObservation, Role, ScanJob, ScanProfile, Site, Subnet, SwitchPort, TopologyLink, TopologyNode, User, UserMfa, Vlan
from app.schemas.api import ArchiveAsset, AssetOut, AssetUpdate, DatacenterDeviceCreate, DnsTest, IpAddressCreate, ManualAssetCreate, MfaCode, PasswordChange, PrefixCreate, PrefixUpdate, ReportEmail, ScanCreate, ScanOut, SiteCreate, SiteOut, SnmpCredentialCreate, SubnetCreate, SubnetOut, TopologyLinkCreate, TopologyLinkUpdate, VlanCreate
from app.services.topology import ensure_asset_node, rebuild_inferred_topology
from app.core.secrets import decrypt_secret, encrypt_secret
from app.services.safety import validate_target
from app.services.vendors import MOBILE_VENDORS,normalize_vendor

router = APIRouter(prefix="/api/v1")


@router.post("/auth/login")
async def login(request:Request,form:OAuth2PasswordRequestForm=Depends(),x_mfa_code:str|None=Header(default=None),db:AsyncSession=Depends(get_db)):
    client=(request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")).split(",")[0].strip()
    limiter=redis.from_url(settings.redis_url,decode_responses=True);key=f"login:{client}:{form.username.casefold()}"
    try:
        attempts=await limiter.incr(key)
        if attempts==1:await limiter.expire(key,300)
        if attempts>5:raise HTTPException(429,"Trop de tentatives. Réessayez dans quelques minutes.",headers={"Retry-After":"300"})
    except HTTPException:raise
    except Exception:pass
    finally:await limiter.aclose()
    user = (await db.execute(select(User).where(User.username == form.username))).scalar_one_or_none()
    if not user or not user.active or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Identifiants invalides")
    mfa=await db.get(UserMfa,user.id)
    if mfa and mfa.enabled:
        secret=decrypt_secret(mfa.encrypted_secret)["secret"]
        if not x_mfa_code:raise HTTPException(401,"MFA_REQUIRED")
        if not pyotp.TOTP(secret).verify(x_mfa_code,valid_window=1):raise HTTPException(401,"Code MFA invalide")
    db.add(AuditLog(user_id=user.id, action="login"))
    await db.commit()
    limiter=redis.from_url(settings.redis_url,decode_responses=True)
    try:await limiter.delete(key)
    finally:await limiter.aclose()
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"username": user.username, "role": user.role.value}}


@router.get("/auth/me")
async def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username, "role": user.role.value}

@router.post("/auth/password")
async def change_password(data:PasswordChange,db:AsyncSession=Depends(get_db),user:User=Depends(current_user)):
    if not verify_password(data.current_password,user.password_hash):raise HTTPException(422,"Mot de passe actuel incorrect")
    if data.current_password==data.new_password:raise HTTPException(422,"Le nouveau mot de passe doit être différent")
    if not (any(c.islower() for c in data.new_password) and any(c.isupper() for c in data.new_password) and any(c.isdigit() for c in data.new_password) and any(not c.isalnum() for c in data.new_password)):raise HTTPException(422,"Utilisez une majuscule, une minuscule, un chiffre et un caractère spécial")
    user.password_hash=hash_password(data.new_password);db.add(AuditLog(user_id=user.id,action="password_changed"));await db.commit();return {"changed":True}


@router.get("/auth/mfa/status")
async def mfa_status(db:AsyncSession=Depends(get_db),user:User=Depends(current_user)):
    row=await db.get(UserMfa,user.id);return {"enabled":bool(row and row.enabled),"pending":bool(row and not row.enabled)}


@router.post("/auth/mfa/setup")
async def mfa_setup(db:AsyncSession=Depends(get_db),user:User=Depends(current_user)):
    secret=pyotp.random_base32();row=await db.get(UserMfa,user.id)
    if not row:row=UserMfa(user_id=user.id,encrypted_secret=encrypt_secret({"secret":secret}));db.add(row)
    else:row.encrypted_secret=encrypt_secret({"secret":secret});row.enabled=False;row.confirmed_at=None
    await db.commit();uri=pyotp.TOTP(secret).provisioning_uri(name=user.username,issuer_name="NetScope")
    return {"secret":secret,"otpauth_uri":uri,"message":"Scannez cette URI puis confirmez avec un code"}


@router.post("/auth/mfa/confirm")
async def mfa_confirm(data:MfaCode,db:AsyncSession=Depends(get_db),user:User=Depends(current_user)):
    row=await db.get(UserMfa,user.id)
    if not row:raise HTTPException(409,"Initialisez d'abord le MFA")
    if not pyotp.TOTP(decrypt_secret(row.encrypted_secret)["secret"]).verify(data.code,valid_window=1):raise HTTPException(422,"Code MFA invalide")
    row.enabled=True;row.confirmed_at=datetime.now(timezone.utc);db.add(AuditLog(user_id=user.id,action="mfa_enabled"));await db.commit();return {"enabled":True}


@router.post("/auth/mfa/disable")
async def mfa_disable(data:MfaCode,db:AsyncSession=Depends(get_db),user:User=Depends(current_user)):
    row=await db.get(UserMfa,user.id)
    if not row or not row.enabled:raise HTTPException(409,"MFA non activé")
    if not pyotp.TOTP(decrypt_secret(row.encrypted_secret)["secret"]).verify(data.code,valid_window=1):raise HTTPException(422,"Code MFA invalide")
    await db.delete(row);db.add(AuditLog(user_id=user.id,action="mfa_disabled"));await db.commit();return {"enabled":False}


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    active=~exists(select(AssetArchive.asset_id).where(AssetArchive.asset_id==Asset.id))
    total = await db.scalar(select(func.count()).select_from(Asset).where(active)) or 0
    counts = dict((await db.execute(select(Asset.status, func.count()).where(active).group_by(Asset.status))).all())
    since = datetime.now(timezone.utc) - timedelta(days=1)
    new = await db.scalar(select(func.count()).select_from(Asset).where(active,Asset.first_seen >= since)) or 0
    by_vendor = (await db.execute(select(Asset.manufacturer, func.count()).where(active).group_by(Asset.manufacturer).order_by(func.count().desc()).limit(8))).all()
    by_type = (await db.execute(select(Asset.device_type, func.count()).where(active).group_by(Asset.device_type).order_by(func.count().desc()))).all()
    by_os = (await db.execute(select(Asset.operating_system, func.count()).where(active).group_by(Asset.operating_system).order_by(func.count().desc()).limit(8))).all()
    scans = (await db.execute(select(ScanJob).order_by(ScanJob.created_at.desc()).limit(5))).scalars().all()
    return {"total": total, "online": counts.get(AssetStatus.online, 0), "offline": counts.get(AssetStatus.offline, 0), "unknown": counts.get(AssetStatus.unknown, 0), "new_24h": new, "by_vendor": [{"label": x or "Inconnu", "value": n} for x,n in by_vendor], "by_type": [{"label": x, "value": n} for x,n in by_type], "by_os": [{"label": x or "Inconnu", "value": n} for x,n in by_os], "recent_scans": [ScanOut.model_validate(s) for s in scans]}


def asset_query():
    return select(Asset).where(~exists(select(AssetArchive.asset_id).where(AssetArchive.asset_id==Asset.id))).options(selectinload(Asset.addresses), selectinload(Asset.identifiers), selectinload(Asset.services))


@router.get("/assets", response_model=list[AssetOut])
async def assets(search: str | None = None, status: str | None = None, device_type: str | None = None, manufacturer: str | None = None, operating_system: str | None = None, recent_hours: int | None = Query(None,ge=1,le=8760), skip: int = 0, limit: int = Query(100, le=500), db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    q = asset_query()
    if search:
        term = f"%{search}%"
        q = q.outerjoin(AssetAddress).where(or_(Asset.hostname.ilike(term), Asset.manufacturer.ilike(term), AssetAddress.address.ilike(term)))
    if status: q = q.where(Asset.status == status)
    if device_type: q = q.where(Asset.device_type == device_type)
    if manufacturer:
        q = q.where(Asset.manufacturer.is_(None) if manufacturer == "Inconnu" else Asset.manufacturer == manufacturer)
    if operating_system:
        q = q.where(Asset.operating_system.is_(None) if operating_system == "Inconnu" else Asset.operating_system == operating_system)
    if recent_hours:q=q.where(Asset.first_seen>=datetime.now(timezone.utc)-timedelta(hours=recent_hours))
    return (await db.execute(q.order_by(Asset.last_seen.desc()).offset(skip).limit(limit))).scalars().unique().all()


@router.get("/assets/export.csv")
async def export_assets(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    rows = (await db.execute(asset_query())).scalars().unique().all()
    out = io.StringIO(); writer = csv.writer(out)
    writer.writerow(["status","ip","mac","hostname","vendor","model","type","os","confidence","first_seen","last_seen"])
    for a in rows:
        writer.writerow([a.status.value, a.addresses[0].address if a.addresses else "", next((i.value for i in a.identifiers if i.kind == "mac"), ""), a.hostname or "", a.manufacturer or "", a.model or "", a.device_type, a.operating_system or "", a.confidence, a.first_seen.isoformat(), a.last_seen.isoformat()])
    db.add(AuditLog(user_id=user.id, action="export_assets", details={"format":"csv"})); await db.commit()
    return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=netscope-assets.csv"})


@router.get("/assets/{asset_id}", response_model=AssetOut)
async def asset(asset_id: str, db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    value = (await db.execute(asset_query().where(Asset.id == asset_id))).scalar_one_or_none()
    if not value: raise HTTPException(404, "Actif introuvable")
    return value


@router.post("/assets",response_model=AssetOut)
async def create_manual_asset(data:ManualAssetCreate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    try:address=str(ipaddress.ip_address(data.ip_address))
    except ValueError as exc:raise HTTPException(422,"Adresse IP invalide") from exc
    if await db.scalar(select(AssetAddress.id).where(AssetAddress.address==address)):raise HTTPException(409,"Cette adresse est déjà associée à un actif")
    mac=data.mac_address.upper() if data.mac_address else None
    if mac and await db.scalar(select(AssetIdentifier.id).where(AssetIdentifier.kind=="mac",AssetIdentifier.value==mac)):raise HTTPException(409,"Cette MAC est déjà associée à un actif")
    asset=Asset(status=AssetStatus.unknown,hostname=data.hostname,manufacturer=normalize_vendor(data.manufacturer),model=data.model,device_type=data.device_type,operating_system=data.operating_system,confidence=1.0);db.add(asset);await db.flush();db.add(AssetAddress(asset_id=asset.id,address=address,version=6 if ":" in address else 4))
    prefix=next((p for p in (await db.execute(select(IpamPrefix))).scalars() if ipaddress.ip_address(address) in ipaddress.ip_network(p.prefix)),None)
    ipam_row=(await db.execute(select(IpamAddress).where(IpamAddress.address==address))).scalar_one_or_none()
    if ipam_row:ipam_row.asset_id=asset.id;ipam_row.prefix_id=ipam_row.prefix_id or (prefix.id if prefix else None);ipam_row.dns_name=data.hostname or ipam_row.dns_name;ipam_row.status="active"
    else:db.add(IpamAddress(address=address,prefix_id=prefix.id if prefix else None,asset_id=asset.id,status="active",dns_name=data.hostname,source="manual",last_seen=datetime.now(timezone.utc)))
    if mac:db.add(AssetIdentifier(asset_id=asset.id,kind="mac",value=mac,confidence=1.0))
    locked=[x for x in ("hostname","manufacturer","model","device_type","operating_system") if getattr(data,x) is not None]
    db.add(AssetMetadata(asset_id=asset.id,role=data.role,owner=data.owner,criticality=data.criticality,notes=data.notes,custom_fields={"_locked_identity_fields":locked}))
    db.add(AssetHistory(asset_id=asset.id,event_type="asset_created_manually",new_value=address));db.add(AuditLog(user_id=user.id,action="asset_created_manually",details={"asset_id":asset.id,"address":address}));await db.commit()
    return (await db.execute(asset_query().where(Asset.id==asset.id))).scalar_one()


@router.delete("/assets/{asset_id}")
async def archive_asset(asset_id:str,data:ArchiveAsset|None=None,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    asset=await db.get(Asset,asset_id)
    if not asset:raise HTTPException(404,"Actif introuvable")
    if await db.get(AssetArchive,asset_id):raise HTTPException(409,"Actif déjà archivé")
    reason=data.reason if data else None;db.add(AssetArchive(asset_id=asset.id,archived_by=user.id,reason=reason));await db.execute(update(IpamAddress).where(IpamAddress.asset_id==asset.id).values(status="deprecated"));db.add(AssetHistory(asset_id=asset.id,event_type="asset_archived",new_value=reason));db.add(AuditLog(user_id=user.id,action="asset_archived",details={"asset_id":asset.id,"reason":reason}));await db.commit();return {"archived":True,"id":asset.id}


@router.post("/assets/{asset_id}/restore")
async def restore_asset(asset_id:str,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin))):
    archive=await db.get(AssetArchive,asset_id)
    if not archive:raise HTTPException(404,"Archive introuvable")
    await db.delete(archive);await db.execute(update(IpamAddress).where(IpamAddress.asset_id==asset_id).values(status="active"));db.add(AssetHistory(asset_id=asset_id,event_type="asset_restored"));db.add(AuditLog(user_id=user.id,action="asset_restored",details={"asset_id":asset_id}));await db.commit();return {"restored":True,"id":asset_id}


@router.get("/archives/assets")
async def archived_assets(db:AsyncSession=Depends(get_db),_=Depends(current_user)):
    rows=(await db.execute(select(AssetArchive,Asset).join(Asset,Asset.id==AssetArchive.asset_id).order_by(AssetArchive.archived_at.desc()))).all();result=[]
    for archive,asset in rows:
        addresses=(await db.execute(select(AssetAddress.address).where(AssetAddress.asset_id==asset.id))).scalars().all()
        result.append({"id":asset.id,"hostname":asset.hostname,"manufacturer":asset.manufacturer,"device_type":asset.device_type,"addresses":addresses,"reason":archive.reason,"archived_at":archive.archived_at})
    return result


@router.get("/assets/{asset_id}/evidence")
async def evidence(asset_id: str, db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    return (await db.execute(select(Evidence).where(Evidence.asset_id == asset_id).order_by(Evidence.observed_at.desc()))).scalars().all()


@router.get("/assets/{asset_id}/history")
async def history(asset_id: str, db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    return (await db.execute(select(AssetHistory).where(AssetHistory.asset_id == asset_id).order_by(AssetHistory.created_at.desc()))).scalars().all()


@router.get("/assets/{asset_id}/raw-observations")
async def raw_observations(asset_id:str,limit:int=Query(50,ge=1,le=200),db:AsyncSession=Depends(get_db),_=Depends(require(Role.admin,Role.operator))):
    targets=(await db.execute(select(AssetAddress.address).where(AssetAddress.asset_id==asset_id))).scalars().all()
    if not targets and not await db.get(Asset,asset_id):raise HTTPException(404,"Actif introuvable")
    rows=(await db.execute(select(RawObservation).where(RawObservation.target.in_(targets)).order_by(RawObservation.observed_at.desc()).limit(limit))).scalars().all()
    return [{"id":x.id,"scan_id":x.scan_id,"source":x.source,"target":x.target,"raw_data":x.raw_data,"observed_at":x.observed_at} for x in rows]


@router.patch("/assets/{asset_id}")
async def update_asset(asset_id:str,data:AssetUpdate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    asset=await db.get(Asset,asset_id)
    if not asset:raise HTTPException(404,"Actif introuvable")
    values=data.model_dump(exclude_unset=True);core=("hostname","manufacturer","model","device_type","operating_system")
    if "manufacturer" in values:values["manufacturer"]=normalize_vendor(values["manufacturer"])
    locked=[]
    for field in core:
        if field in values:
            old=getattr(asset,field);new=values.pop(field);setattr(asset,field,new)
            locked.append(field)
            if old!=new:db.add(AssetHistory(asset_id=asset.id,event_type=f"manual_{field}_changed",old_value=old,new_value=new))
    metadata=await db.get(AssetMetadata,asset.id)
    if not metadata:metadata=AssetMetadata(asset_id=asset.id);db.add(metadata)
    for field,value in values.items():setattr(metadata,field,value)
    custom=dict(metadata.custom_fields or {});custom["_locked_identity_fields"]=sorted(set(custom.get("_locked_identity_fields",[]))|set(locked));metadata.custom_fields=custom
    db.add(AuditLog(user_id=user.id,action="asset_updated",details={"asset_id":asset.id,"fields":list(data.model_dump(exclude_unset=True))}));await db.commit()
    return {"id":asset.id,"updated":True}


@router.get("/assets/{asset_id}/metadata")
async def asset_metadata(asset_id:str,db:AsyncSession=Depends(get_db),_=Depends(current_user)):
    row=await db.get(AssetMetadata,asset_id)
    return {"asset_id":asset_id,"serial_number":row.serial_number if row else None,"role":row.role if row else None,"platform":row.platform if row else None,"owner":row.owner if row else None,"criticality":row.criticality if row else None,"notes":row.notes if row else None,"custom_fields":row.custom_fields if row else {}}


@router.get("/sites", response_model=list[SiteOut])
async def sites(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    return (await db.execute(select(Site).order_by(Site.name))).scalars().all()


@router.post("/sites", response_model=SiteOut)
async def create_site(data:SiteCreate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    if await db.scalar(select(Site.id).where(func.lower(Site.name)==data.name.strip().lower())):raise HTTPException(409,"Un site portant ce nom existe déjà")
    row=Site(name=data.name.strip(),description=data.description);db.add(row);db.add(AuditLog(user_id=user.id,action="site_created",details={"name":row.name}));await db.commit();await db.refresh(row);return row

@router.delete("/sites/{site_id}")
async def delete_site(site_id:str,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin))):
    row=await db.get(Site,site_id)
    if not row:raise HTTPException(404,"Site introuvable")
    dependencies=sum([await db.scalar(select(func.count()).select_from(model).where(model.site_id==site_id)) or 0 for model in (Asset,Subnet,IpamPrefix,Vlan,Credential)])
    if dependencies:raise HTTPException(409,f"Ce site est encore utilisé par {dependencies} objet(s). Déplacez-les ou supprimez-les d'abord.")
    name=row.name;await db.delete(row);db.add(AuditLog(user_id=user.id,action="site_deleted",details={"name":name}));await db.commit();return {"deleted":True}


@router.get("/networks", response_model=list[SubnetOut])
async def networks(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    return (await db.execute(select(Subnet).order_by(Subnet.cidr))).scalars().all()


@router.post("/networks", response_model=SubnetOut)
async def create_network(data: SubnetCreate, db: AsyncSession = Depends(get_db), user:User=Depends(require(Role.admin, Role.operator))):
    normalized = validate_target(data.cidr, confirm_large=True, confirm_public=False)
    if await db.scalar(select(Subnet.id).where(Subnet.cidr==normalized)):raise HTTPException(409,"Ce réseau est déjà enregistré")
    row = Subnet(**data.model_dump(exclude={"cidr"}), cidr=normalized); db.add(row)
    db.add(AuditLog(user_id=user.id,action="network_created",details={"cidr":normalized,"name":data.name}));await db.commit();await db.refresh(row);return row


@router.delete("/networks/{network_id}")
async def delete_network(network_id:str,purge_ipam:bool=False,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin))):
    row=await db.get(Subnet,network_id)
    if not row:raise HTTPException(404,"Réseau introuvable")
    prefix=(await db.execute(select(IpamPrefix).where(IpamPrefix.prefix==row.cidr))).scalar_one_or_none()
    address_count=0
    if prefix:
        address_count=await db.scalar(select(func.count()).select_from(IpamAddress).where(IpamAddress.prefix_id==prefix.id)) or 0
        if not purge_ipam:
            raise HTTPException(409,f"Ce réseau est lié à un préfixe IPAM contenant {address_count} adresse(s). Confirmez la suppression IPAM.")
        # Les actifs et observations restent intacts : seuls les objets de gestion IPAM sont retirés.
        for address in (await db.execute(select(IpamAddress).where(IpamAddress.prefix_id==prefix.id))).scalars():await db.delete(address)
        await db.delete(prefix)
    cidr=row.cidr;await db.delete(row)
    db.add(AuditLog(user_id=user.id,action="network_deleted",details={"cidr":cidr,"purge_ipam":purge_ipam,"ipam_addresses_deleted":address_count}));await db.commit()
    return {"deleted":True,"cidr":cidr,"ipam_prefix_deleted":bool(prefix),"ipam_addresses_deleted":address_count}


@router.get("/scan-profiles")
async def profiles(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    return (await db.execute(select(ScanProfile).order_by(ScanProfile.name))).scalars().all()


@router.get("/scans", response_model=list[ScanOut])
async def scans(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    return (await db.execute(select(ScanJob).order_by(ScanJob.created_at.desc()).limit(100))).scalars().all()


@router.post("/scans", response_model=ScanOut)
async def create_scan(data: ScanCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require(Role.admin, Role.operator))):
    target = validate_target(data.target, data.confirm_large_network, data.confirm_public_network)
    profile = await db.get(ScanProfile, data.profile_id)
    if not profile: raise HTTPException(404, "Profil introuvable")
    active = await db.scalar(select(func.count()).select_from(ScanJob).where(ScanJob.target == target, ScanJob.status.in_(["queued","running"])))
    if active: raise HTTPException(409, "Un scan de cette cible est déjà actif")
    if "snmp" in profile.modules and not data.credential_id: raise HTTPException(422,"Un identifiant SNMPv3 est requis pour ce profil")
    if data.credential_id and not await db.get(Credential,data.credential_id): raise HTTPException(404,"Identifiant SNMPv3 introuvable")
    row = ScanJob(target=target, profile_id=profile.id, credential_id=data.credential_id, created_by=user.id); db.add(row); db.add(AuditLog(user_id=user.id, action="scan_created", details={"target":target})); await db.commit(); await db.refresh(row)
    try:
        from app.workers.tasks import execute_scan
        execute_scan.apply_async(args=[row.id],queue="scanner",retry=False)
    except Exception as exc:
        row.status="failed";row.error="Impossible de joindre la file de tâches";row.finished_at=datetime.now(timezone.utc);await db.commit()
        raise HTTPException(503,"Scanner temporairement indisponible") from exc
    return row


@router.get("/vlans")
async def vlans(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    rows=(await db.execute(select(Vlan).order_by(Vlan.vlan_id))).scalars().all()
    return [{"id":x.id,"vlan_id":x.vlan_id,"name":x.name,"site_id":x.site_id,"source":x.source,"last_seen":x.last_seen} for x in rows]

@router.post("/vlans")
async def create_vlan(data:VlanCreate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    if data.site_id and not await db.get(Site,data.site_id):raise HTTPException(404,"Site introuvable")
    prefix=await db.get(IpamPrefix,data.prefix_id)
    if not prefix:raise HTTPException(404,"Préfixe IPAM introuvable : enregistrez d'abord le réseau")
    if prefix.vlan_id:raise HTTPException(409,"Ce préfixe est déjà affecté à un VLAN")
    if await db.scalar(select(Vlan.id).where(Vlan.site_id==data.site_id,Vlan.vlan_id==data.vlan_id)):raise HTTPException(409,"Ce numéro de VLAN existe déjà sur ce site")
    row=Vlan(vlan_id=data.vlan_id,name=data.name,site_id=data.site_id,source="manual");db.add(row);await db.flush();prefix.vlan_id=row.id
    db.add(AuditLog(user_id=user.id,action="vlan_created",details={"vlan_id":row.vlan_id,"prefix":prefix.prefix}));await db.commit();await db.refresh(row);return {"id":row.id,"vlan_id":row.vlan_id,"name":row.name,"site_id":row.site_id,"prefix_id":prefix.id}

@router.delete("/vlans/{vlan_id}")
async def delete_vlan(vlan_id:str,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin))):
    row=await db.get(Vlan,vlan_id)
    if not row:raise HTTPException(404,"VLAN introuvable")
    for prefix in (await db.execute(select(IpamPrefix).where(IpamPrefix.vlan_id==row.id))).scalars():prefix.vlan_id=None
    number=row.vlan_id;await db.delete(row);db.add(AuditLog(user_id=user.id,action="vlan_deleted",details={"vlan_id":number}));await db.commit();return {"deleted":True}

@router.post("/datacenter/equipment",response_model=AssetOut)
async def create_datacenter_equipment(data:DatacenterDeviceCreate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    if not await db.get(Site,data.site_id):raise HTTPException(404,"Site introuvable")
    vlan=await db.get(Vlan,data.vlan_id)
    if not vlan or vlan.site_id!=data.site_id:raise HTTPException(422,"VLAN introuvable pour ce site")
    prefix=(await db.execute(select(IpamPrefix).where(IpamPrefix.vlan_id==vlan.id))).scalar_one_or_none()
    if not prefix:raise HTTPException(422,"Le VLAN doit être associé à un réseau IPAM enregistré")
    try:address=str(ipaddress.ip_address(data.ip_address))
    except ValueError as exc:raise HTTPException(422,"Adresse IP invalide") from exc
    if ipaddress.ip_address(address) not in ipaddress.ip_network(prefix.prefix):raise HTTPException(422,f"L'adresse doit appartenir au réseau {prefix.prefix}")
    if await db.scalar(select(IpamAddress.id).where(IpamAddress.address==address)):raise HTTPException(409,"Cette adresse IP est déjà utilisée")
    asset=Asset(status=AssetStatus.unknown,hostname=data.hostname,manufacturer=normalize_vendor(data.manufacturer),model=data.model,device_type=data.device_type,operating_system=data.operating_system,site_id=data.site_id,confidence=1);db.add(asset);await db.flush()
    db.add(AssetAddress(asset_id=asset.id,address=address,version=6 if ":" in address else 4));db.add(IpamAddress(address=address,prefix_id=prefix.id,asset_id=asset.id,status="active",dns_name=data.hostname,description=data.description,role="datacenter",source="manual"));db.add(AssetMetadata(asset_id=asset.id,notes=data.description,role="datacenter"))
    for service in data.services:db.add(AssetService(asset_id=asset.id,protocol=service.protocol,port=service.port,name=service.name))
    db.add(AuditLog(user_id=user.id,action="datacenter_equipment_created",details={"asset_id":asset.id,"site_id":data.site_id,"vlan_id":vlan.vlan_id,"address":address}));await db.commit()
    return await db.scalar(select(Asset).options(selectinload(Asset.addresses),selectinload(Asset.identifiers),selectinload(Asset.services)).where(Asset.id==asset.id))


@router.get("/topology")
async def topology(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    nodes=(await db.execute(select(TopologyNode))).scalars().all();links=(await db.execute(select(TopologyLink))).scalars().all()
    return {"status":"active","nodes":[{"id":x.id,"asset_id":x.asset_id,"label":x.label,"kind":x.kind} for x in nodes],"links":[{"id":x.id,"source":x.source_node_id,"target":x.target_node_id,"source_port":x.source_port,"target_port":x.target_port,"protocol":x.source,"confidence":x.confidence} for x in links]}


@router.post("/topology/refresh")
async def refresh_topology(db:AsyncSession=Depends(get_db),_=Depends(require(Role.admin,Role.operator))):
    created=await rebuild_inferred_topology(db);return {"created":created,"status":"refreshed"}


@router.post("/topology/links")
async def create_topology_link(data:TopologyLinkCreate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    source=await db.get(Asset,data.source_asset_id);target=await db.get(Asset,data.target_asset_id)
    if not source or not target:raise HTTPException(404,"Actif source ou destination introuvable")
    if source.id==target.id:raise HTTPException(422,"La source et la destination doivent être différentes")
    source_node=await ensure_asset_node(db,source);target_node=await ensure_asset_node(db,target)
    existing=(await db.execute(select(TopologyLink).where(TopologyLink.source_node_id==source_node.id,TopologyLink.target_node_id==target_node.id,TopologyLink.source=="manual"))).scalar_one_or_none()
    if existing:raise HTTPException(409,"Cette relation manuelle existe déjà")
    row=TopologyLink(source_node_id=source_node.id,target_node_id=target_node.id,source_port=data.source_port,target_port=data.target_port,source="manual",confidence=1.0);db.add(row);db.add(AuditLog(user_id=user.id,action="topology_link_created",details={"source_asset_id":source.id,"target_asset_id":target.id,"description":data.description}));await db.commit();return {"id":row.id,"created":True}


@router.delete("/topology/links/{link_id}")
async def delete_topology_link(link_id:str,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    row=await db.get(TopologyLink,link_id)
    if not row:raise HTTPException(404,"Relation introuvable")
    await db.delete(row);db.add(AuditLog(user_id=user.id,action="topology_link_deleted",details={"link_id":link_id,"source":row.source}));await db.commit();return {"deleted":True}

@router.patch("/topology/links/{link_id}")
async def update_topology_link(link_id:str,data:TopologyLinkUpdate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    row=await db.get(TopologyLink,link_id)
    if not row:raise HTTPException(404,"Relation introuvable")
    if row.source!="manual":raise HTTPException(409,"Une relation collectée ou inférée est en lecture seule. Modifiez la source réseau ou créez une relation manuelle.")
    row.source_port=data.source_port.strip() if data.source_port else None;row.target_port=data.target_port.strip() if data.target_port else None
    if data.reverse:row.source_node_id,row.target_node_id=row.target_node_id,row.source_node_id;row.source_port,row.target_port=row.target_port,row.source_port
    db.add(AuditLog(user_id=user.id,action="topology_link_updated",details={"link_id":row.id,"reverse":data.reverse}));await db.commit();return {"id":row.id,"updated":True}


@router.get("/network-devices")
async def network_devices(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    devices=(await db.execute(select(NetworkDevice))).scalars().all();result=[]
    for device in devices:
        ports=(await db.execute(select(SwitchPort).where(SwitchPort.network_device_id==device.id))).scalars().all()
        result.append({"id":device.id,"asset_id":device.asset_id,"management_ip":device.management_ip,"sys_name":device.sys_name,"sys_descr":device.sys_descr,"sys_object_id":device.sys_object_id,"last_polled":device.last_polled,"ports":[{"id":p.id,"if_index":p.if_index,"name":p.name,"description":p.description,"admin_status":p.admin_status,"oper_status":p.oper_status,"vlan_id":p.vlan_id} for p in ports]})
    return result


@router.get("/switch-ports/{port_id}/macs")
async def port_macs(port_id:str,db:AsyncSession=Depends(get_db),_=Depends(current_user)):
    return (await db.execute(select(PortMacEntry).where(PortMacEntry.switch_port_id==port_id))).scalars().all()


@router.post("/credentials/snmpv3")
async def create_snmp_credential(data:SnmpCredentialCreate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin))):
    secret=data.model_dump(exclude={"name","site_id"});secret["version"]="3"
    row=Credential(name=data.name,kind="snmpv3",site_id=data.site_id,encrypted_secret=encrypt_secret(secret));db.add(row)
    db.add(AuditLog(user_id=user.id,action="credential_created",details={"id":row.id,"kind":"snmpv3","name":row.name}));await db.commit();await db.refresh(row)
    return {"id":row.id,"name":row.name,"kind":row.kind,"site_id":row.site_id,"created_at":row.created_at}


@router.get("/credentials")
async def credentials(db:AsyncSession=Depends(get_db),_=Depends(require(Role.admin))):
    rows=(await db.execute(select(Credential).order_by(Credential.name))).scalars().all()
    return [{"id":x.id,"name":x.name,"kind":x.kind,"site_id":x.site_id,"created_at":x.created_at} for x in rows]


@router.get("/vendors")
async def vendors(db: AsyncSession = Depends(get_db), _=Depends(current_user)):
    active=~exists(select(AssetArchive.asset_id).where(AssetArchive.asset_id==Asset.id))
    grouped=(await db.execute(select(Asset.manufacturer,Asset.device_type,func.count()).where(active,Asset.manufacturer.is_not(None)).group_by(Asset.manufacturer,Asset.device_type))).all()
    counts:dict[str,int]={};types:dict[str,set[str]]={};type_counts:dict[str,dict[str,int]]={}
    for name,device_type,count in grouped:
        kind=device_type or "unknown";counts[name]=counts.get(name,0)+count;types.setdefault(name,set()).add(kind);type_counts.setdefault(name,{})[kind]=count
    names=sorted(set(counts)|set(MOBILE_VENDORS),key=str.casefold)
    return [{"name":name,"assets":counts.get(name,0),"category":"mobile" if name in MOBILE_VENDORS else "infrastructure","device_types":sorted(types.get(name,set())),"device_type_counts":type_counts.get(name,{})} for name in names]


@router.get("/ipam/prefixes")
async def ipam_prefixes(db:AsyncSession=Depends(get_db),_=Depends(current_user)):
    prefixes=(await db.execute(select(IpamPrefix).order_by(IpamPrefix.prefix))).scalars().all();result=[]
    usage=dict((await db.execute(select(IpamAddress.prefix_id,func.count()).where(IpamAddress.prefix_id.is_not(None)).group_by(IpamAddress.prefix_id))).all())
    for prefix in prefixes:
        used=usage.get(prefix.id,0)
        size=max(ipaddress.ip_network(prefix.prefix).num_addresses-2,1)
        result.append({"id":prefix.id,"prefix":prefix.prefix,"name":prefix.name,"status":prefix.status,"role":prefix.role,"vlan_id":prefix.vlan_id,"site_id":prefix.site_id,"gateway":prefix.gateway,"dns_servers":prefix.dns_servers,"description":prefix.description,"used":used,"available":max(size-used,0),"utilization":round(used/size*100,2)})
    return result


@router.post("/ipam/prefixes")
async def create_prefix(data:PrefixCreate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    try:prefix=str(ipaddress.ip_network(data.prefix,strict=False))
    except ValueError as exc:raise HTTPException(422,"Préfixe invalide") from exc
    existing=await db.scalar(select(IpamPrefix.id).where(IpamPrefix.prefix==prefix))
    if existing:raise HTTPException(409,"Ce préfixe existe déjà. Modifiez sa configuration DNS dans la liste.")
    if data.gateway and ipaddress.ip_address(data.gateway) not in ipaddress.ip_network(prefix):raise HTTPException(422,"La passerelle doit appartenir au préfixe")
    row=IpamPrefix(**data.model_dump(exclude={"prefix"}),prefix=prefix);db.add(row);await db.flush()
    if not await db.scalar(select(Subnet.id).where(Subnet.cidr==prefix)):db.add(Subnet(cidr=prefix,name=data.name,state="authorized",site_id=data.site_id))
    network=ipaddress.ip_network(prefix)
    for found in (await db.execute(select(AssetAddress))).scalars():
        if ipaddress.ip_address(found.address) in network:
            asset=await db.get(Asset,found.asset_id)
            exists=await db.scalar(select(IpamAddress.id).where(IpamAddress.address==found.address))
            if not exists:db.add(IpamAddress(address=found.address,prefix_id=row.id,asset_id=found.asset_id,status="active",dns_name=asset.hostname if asset else None,source="discovery",last_seen=found.last_seen))
    db.add(AuditLog(user_id=user.id,action="ipam_prefix_created",details={"prefix":prefix}));await db.commit();await db.refresh(row);return {"id":row.id,"prefix":row.prefix,"name":row.name,"status":row.status}


@router.patch("/ipam/prefixes/{prefix_id}")
async def update_prefix(prefix_id:str,data:PrefixUpdate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    row=await db.get(IpamPrefix,prefix_id)
    if not row:raise HTTPException(404,"Préfixe introuvable")
    values=data.model_dump(exclude_unset=True)
    if "dns_servers" in values:
        try:values["dns_servers"]=[str(ipaddress.ip_address(x)) for x in values["dns_servers"]]
        except ValueError as exc:raise HTTPException(422,"Adresse de serveur DNS invalide") from exc
    for field,value in values.items():setattr(row,field,value)
    db.add(AuditLog(user_id=user.id,action="ipam_prefix_updated",details={"prefix":row.prefix,"fields":list(values)}));await db.commit();return {"id":row.id,"prefix":row.prefix,"dns_servers":row.dns_servers,"updated":True}


@router.delete("/ipam/prefixes/{prefix_id}")
async def delete_prefix(prefix_id:str,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin))):
    row=await db.get(IpamPrefix,prefix_id)
    if not row:raise HTTPException(404,"Préfixe introuvable")
    count=await db.scalar(select(func.count()).select_from(IpamAddress).where(IpamAddress.prefix_id==prefix_id)) or 0
    if count:raise HTTPException(409,f"Ce préfixe contient {count} adresse(s). Supprimez ou déplacez-les d'abord.")
    subnet=(await db.execute(select(Subnet).where(Subnet.cidr==row.prefix))).scalar_one_or_none()
    if subnet:await db.delete(subnet)
    prefix=row.prefix;await db.delete(row);db.add(AuditLog(user_id=user.id,action="ipam_prefix_deleted",details={"prefix":prefix}));await db.commit();return {"deleted":True}


@router.post("/dns/test")
async def test_dns(data:DnsTest,_=Depends(require(Role.admin,Role.operator))):
    try:server=str(ipaddress.ip_address(data.server));address=str(ipaddress.ip_address(data.ip_address))
    except ValueError as exc:raise HTTPException(422,"Serveur DNS ou adresse test invalide") from exc
    resolver=dns.resolver.Resolver(configure=False);resolver.nameservers=[server];resolver.timeout=2;resolver.lifetime=3;started=time.perf_counter()
    try:
        answers=await asyncio.to_thread(resolver.resolve,dns.reversename.from_address(address),"PTR")
        names=[str(x).rstrip(".") for x in answers]
        return {"success":True,"server":server,"ip_address":address,"names":names,"latency_ms":round((time.perf_counter()-started)*1000,1)}
    except dns.resolver.NXDOMAIN:return {"success":False,"server":server,"ip_address":address,"error":"Aucun enregistrement PTR (NXDOMAIN)"}
    except dns.resolver.Timeout:return {"success":False,"server":server,"ip_address":address,"error":"Délai DNS dépassé"}
    except Exception as exc:return {"success":False,"server":server,"ip_address":address,"error":str(exc)[:300]}


@router.get("/ipam/addresses")
async def ipam_addresses(prefix_id:str|None=None,search:str|None=None,db:AsyncSession=Depends(get_db),_=Depends(current_user)):
    q=select(IpamAddress).order_by(IpamAddress.address)
    if prefix_id:q=q.where(IpamAddress.prefix_id==prefix_id)
    if search:q=q.where(or_(IpamAddress.address.ilike(f"%{search}%"),IpamAddress.dns_name.ilike(f"%{search}%")))
    rows=(await db.execute(q.limit(1000))).scalars().all()
    return [{"id":x.id,"address":x.address,"prefix_id":x.prefix_id,"asset_id":x.asset_id,"status":x.status,"role":x.role,"dns_name":x.dns_name,"description":x.description,"source":x.source,"last_seen":x.last_seen} for x in rows]


@router.post("/ipam/addresses")
async def create_ip_address(data:IpAddressCreate,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    try:address=str(ipaddress.ip_interface(data.address).ip)
    except ValueError as exc:raise HTTPException(422,"Adresse IP invalide") from exc
    prefix_id=data.prefix_id
    if prefix_id:
        prefix=await db.get(IpamPrefix,prefix_id)
        if not prefix:raise HTTPException(404,"Préfixe introuvable")
        if ipaddress.ip_address(address) not in ipaddress.ip_network(prefix.prefix):raise HTTPException(422,"Adresse hors du préfixe")
    row=IpamAddress(**data.model_dump(exclude={"address"}),address=address,source="manual");db.add(row);db.add(AuditLog(user_id=user.id,action="ipam_address_created",details={"address":address}));await db.commit();await db.refresh(row);return {"id":row.id,"address":row.address,"status":row.status}


@router.delete("/ipam/addresses/{address_id}")
async def delete_ipam_address(address_id:str,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    row=await db.get(IpamAddress,address_id)
    if not row:raise HTTPException(404,"Adresse IPAM introuvable")
    address=row.address;await db.delete(row);db.add(AuditLog(user_id=user.id,action="ipam_address_deleted",details={"address":address,"source":row.source}));await db.commit();return {"deleted":True}


@router.get("/device-roles")
async def device_roles(db:AsyncSession=Depends(get_db),_=Depends(current_user)):
    return (await db.execute(select(DeviceRole).order_by(DeviceRole.name))).scalars().all()

REPORT_LABELS={"inventory":"Inventaire des équipements","ipam":"État IPAM et utilisation","scans":"Historique des scans","vendors":"Constructeurs et catégories","security":"Journal de sécurité"}

@router.get("/smtp/status")
async def smtp_status(_=Depends(require(Role.admin))):
    return {"configured":bool(settings.smtp_host and settings.smtp_sender_list),"host":settings.smtp_host or None,"port":settings.smtp_port,"tls":settings.smtp_use_tls,"ssl":settings.smtp_use_ssl,"senders":settings.smtp_sender_list}

@router.get("/reports/options")
async def report_options(_=Depends(current_user)):
    return [{"id":key,"label":label} for key,label in REPORT_LABELS.items()]

async def build_report(kind:str,db:AsyncSession)->tuple[str,str]:
    out=io.StringIO();writer=csv.writer(out)
    if kind=="inventory":
        writer.writerow(["IP","Nom","Constructeur","Modèle","Type","Système","État","Dernier vu"])
        for a in (await db.execute(asset_query())).scalars().unique():writer.writerow([a.addresses[0].address if a.addresses else "",a.hostname or "",a.manufacturer or "",a.model or "",a.device_type,a.operating_system or "",a.status.value,a.last_seen.isoformat()])
    elif kind=="ipam":
        writer.writerow(["Préfixe","Nom","Rôle","Passerelle","DNS","Adresses utilisées"])
        for p in (await db.execute(select(IpamPrefix).order_by(IpamPrefix.prefix))).scalars():writer.writerow([p.prefix,p.name,p.role or "",p.gateway or "",", ".join(p.dns_servers or []),await db.scalar(select(func.count()).select_from(IpamAddress).where(IpamAddress.prefix_id==p.id)) or 0])
    elif kind=="scans":
        writer.writerow(["Cible","État","Créé","Début","Fin","Erreur"])
        for s in (await db.execute(select(ScanJob).order_by(ScanJob.created_at.desc()).limit(500))).scalars():writer.writerow([s.target,s.status,s.created_at,s.started_at or "",s.finished_at or "",s.error or ""])
    elif kind=="vendors":
        writer.writerow(["Constructeur","Type","Actifs"])
        for name,device_type,count in (await db.execute(select(Asset.manufacturer,Asset.device_type,func.count()).where(Asset.manufacturer.is_not(None)).group_by(Asset.manufacturer,Asset.device_type))).all():writer.writerow([name,device_type,count])
    else:
        writer.writerow(["Date","Utilisateur","Action","Détails"])
        for log in (await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(1000))).scalars():writer.writerow([log.created_at,log.user_id or "système",log.action,json.dumps(log.details or {},ensure_ascii=False)])
    return f"netscope-{kind}-{datetime.now().strftime('%Y%m%d-%H%M')}.csv",out.getvalue()

@router.post("/reports/email")
async def email_report(data:ReportEmail,db:AsyncSession=Depends(get_db),user:User=Depends(require(Role.admin,Role.operator))):
    if not settings.smtp_host:raise HTTPException(503,"SMTP non configuré dans .env")
    if data.sender not in settings.smtp_sender_list:raise HTTPException(422,"Expéditeur non autorisé")
    email_pattern=re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    if not email_pattern.match(data.sender) or any(not email_pattern.match(x) for x in data.recipients):raise HTTPException(422,"Adresse e-mail invalide")
    filename,content=await build_report(data.report_type,db);msg=EmailMessage();msg["From"]=data.sender;msg["To"]=", ".join(data.recipients);msg["Subject"]=data.subject or f"NetScope — {REPORT_LABELS[data.report_type]}";msg.set_content(data.message or "Veuillez trouver le rapport NetScope en pièce jointe.");msg.add_attachment(content.encode("utf-8-sig"),maintype="text",subtype="csv",filename=filename)
    def send():
        smtp_class=smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
        with smtp_class(settings.smtp_host,settings.smtp_port,timeout=settings.smtp_timeout) as client:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:client.starttls()
            if settings.smtp_username:client.login(settings.smtp_username,settings.smtp_password)
            client.send_message(msg)
    try:await asyncio.to_thread(send)
    except Exception as exc:raise HTTPException(502,"Échec de l'envoi SMTP. Vérifiez la configuration et les journaux.") from exc
    db.add(AuditLog(user_id=user.id,action="report_emailed",details={"report_type":data.report_type,"sender":data.sender,"recipients":data.recipients}));await db.commit();return {"sent":True,"filename":filename,"recipients":data.recipients}
