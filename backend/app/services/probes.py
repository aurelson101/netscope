import hmac
import ipaddress
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Probe
from app.services.passive import issue_connector_token,token_digest
from app.services.alerts import open_alert

def issue_probe_token(probe_id:str)->tuple[str,str]:return issue_connector_token(probe_id)

async def authenticate_probe(db:AsyncSession,token:str|None)->Probe:
    if not token or "." not in token:raise HTTPException(401,"Jeton de sonde manquant ou invalide")
    probe=await db.get(Probe,token.split(".",1)[0])
    if not probe or not probe.enabled or not hmac.compare_digest(probe.token_hash,token_digest(token)):raise HTTPException(401,"Jeton de sonde invalide")
    return probe

def observation_in_scope(scan_target:str,observation_target:str)->bool:
    try:return ipaddress.ip_address(observation_target) in ipaddress.ip_network(scan_target,strict=False)
    except ValueError:return False

async def evaluate_probe_health(db:AsyncSession,offline_minutes:int=5)->int:
    now=datetime.now(timezone.utc);cutoff=now-timedelta(minutes=offline_minutes);opened=0
    rows=(await db.execute(select(Probe).where(Probe.enabled.is_(True)))).scalars().all()
    for probe in rows:
        seen=probe.last_seen_at or probe.created_at
        if seen and (seen if seen.tzinfo else seen.replace(tzinfo=timezone.utc))<cutoff:
            await open_alert(db,fingerprint=f"probe_offline:{probe.id}",kind="probe_offline",severity="critical",title="Sonde distante hors ligne",message=f"La sonde {probe.name} ne contacte plus NetScope.",details={"probe_id":probe.id,"name":probe.name,"last_seen_at":probe.last_seen_at.isoformat() if probe.last_seen_at else None});opened+=1
    await db.commit();return opened
