import asyncio
import ipaddress
from datetime import datetime, timezone
from celery import Celery
from celery.signals import after_setup_logger
from sqlalchemy import select
from app.core.config import settings
from app.core.logging import configure_logging
import logging
from app.db.session import SessionLocal
from app.discovery.arp.plugin import ArpPlugin
from app.discovery.dns.plugin import DNSPlugin
from app.discovery.icmp.plugin import IcmpPlugin
from app.discovery.nmap.plugin import NmapPlugin
from app.discovery.snmp.plugin import SnmpPlugin
from app.correlation.engine import correlate
from app.core.secrets import decrypt_secret
from app.models import Credential, IpamPrefix, ScanJob, ScanProfile

configure_logging();logger=logging.getLogger("netscope.worker")
celery=Celery("netscope",broker=settings.redis_url,backend=settings.redis_url)
celery.conf.task_routes={"execute_scan":{"queue":"scanner"}}
plugins={p.name:p for p in [IcmpPlugin(),ArpPlugin(),NmapPlugin(),DNSPlugin(),SnmpPlugin()]}

def module_targets(module:str,target:str,discovered:set[str])->list[str]:
    if module in ("dns","snmp") and "/" in target:
        if discovered:return sorted(discovered,key=lambda value:(ipaddress.ip_address(value).version,int(ipaddress.ip_address(value))))
        network=ipaddress.ip_network(target,strict=False)
        if network.num_addresses==1:return [str(network.network_address)]
        return []
    return [target]


@after_setup_logger.connect(weak=False)
def setup_celery_file_logging(**kwargs):
    configure_logging()


@celery.task(name="execute_scan")
def execute_scan(job_id:str): return asyncio.run(_execute(job_id))


async def _execute(job_id:str):
    async with SessionLocal() as db:
        try:
            job=await db.get(ScanJob,job_id)
            if not job:return
            profile=await db.get(ScanProfile,job.profile_id)
            if not profile:raise ValueError("Profil de scan introuvable")
            job.status="running"; job.started_at=datetime.now(timezone.utc); await db.commit()
            logger.info("scan_started",extra={"job_id":job.id,"target":job.target})
            discovered_targets:set[str]=set()
            for module in profile.modules:
                options=dict(profile.options.get(module,{}))
                if module=="snmp":
                    credential_id=job.credential_id or profile.options.get("credential_id")
                    credential=await db.get(Credential,credential_id) if credential_id else None
                    default=settings.snmp_default_credential
                    if not credential and not default:raise ValueError("Aucun identifiant SNMP affecté au profil et aucun défaut configuré dans .env")
                    options["credential"]=decrypt_secret(credential.encrypted_secret) if credential else default
                targets=module_targets(module,job.target,discovered_targets)
                if module=="snmp" and not targets:raise ValueError("Aucun hôte actif découvert à interroger en SNMP")
                if module=="dns" and "/" in job.target:
                    prefixes=(await db.execute(select(IpamPrefix))).scalars().all()
                    matching=next((p for p in prefixes if p.prefix==job.target),None)
                    if matching and matching.dns_servers:options["servers"]=matching.dns_servers
                for target in targets:
                    for result in await plugins[module].discover(target,options):
                        discovered_targets.add(result.target);await correlate(db,result,job.id)
            job.status="completed"
        except Exception as exc:
            await db.rollback()
            job=await db.get(ScanJob,job_id)
            if job:job.status="failed";job.error=str(exc)[:2000];job.finished_at=datetime.now(timezone.utc);await db.commit()
            logger.exception("scan_failed",extra={"job_id":job_id})
            return
        job.finished_at=datetime.now(timezone.utc); await db.commit();logger.info("scan_completed",extra={"job_id":job.id,"target":job.target})
