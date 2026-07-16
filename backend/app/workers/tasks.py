import asyncio
import ipaddress
from datetime import datetime, timedelta, timezone
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
from app.models import Credential, IpamPrefix, ReportSchedule, ScanJob, ScanProfile, ScanSchedule
from app.services.alerts import evaluate_asset_lifecycle,open_alert

configure_logging();logger=logging.getLogger("netscope.worker")
celery=Celery("netscope",broker=settings.redis_url,backend=settings.redis_url)
celery.conf.task_routes={"execute_scan":{"queue":"scanner"}}
celery.conf.beat_schedule={"dispatch-due-schedules":{"task":"dispatch_due_schedules","schedule":60.0},"evaluate-asset-lifecycle":{"task":"evaluate_asset_lifecycle","schedule":float(settings.lifecycle_interval_seconds)}}
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
            unsupported=set(profile.modules)-set(plugins)
            if unsupported:raise ValueError("Modules de scan non supportés: "+", ".join(sorted(unsupported)))
            job.status="running";job.progress=0;job.result_count=0;job.started_at=datetime.now(timezone.utc);await db.commit()
            logger.info("scan_started",extra={"job_id":job.id,"target":job.target})
            discovered_targets:set[str]=set()
            module_count=max(len(profile.modules),1)
            for module_index,module in enumerate(profile.modules):
                job.current_module=module;job.progress=int(module_index/module_count*100);await db.commit()
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
                    matching=next((p for p in prefixes if p.prefix==job.target and p.vrf_id==job.vrf_id),None)
                    if matching and matching.dns_servers:options["servers"]=matching.dns_servers
                for target in targets:
                    for result in await plugins[module].discover(target,options):
                        discovered_targets.add(result.target);await correlate(db,result,job.id,job.vrf_id);job.result_count+=1
                job.progress=int((module_index+1)/module_count*100);await db.commit()
            job.status="completed";job.current_module=None;job.progress=100
        except Exception as exc:
            await db.rollback()
            job=await db.get(ScanJob,job_id)
            if job:job.status="failed";job.current_module=None;job.error=str(exc)[:2000];job.finished_at=datetime.now(timezone.utc);await db.commit()
            if job:
                await open_alert(db,fingerprint=f"scan_failed:{job.id}",kind="scan_failed",severity="warning",title="Échec d'un scan réseau",message=f"Le scan de {job.target} a échoué : {str(exc)[:500]}",details={"scan_id":job.id,"target":job.target});await db.commit()
            logger.exception("scan_failed",extra={"job_id":job_id})
            return
        job.finished_at=datetime.now(timezone.utc); await db.commit();logger.info("scan_completed",extra={"job_id":job.id,"target":job.target})

@celery.task(name="evaluate_asset_lifecycle")
def evaluate_asset_lifecycle_task():return asyncio.run(_evaluate_asset_lifecycle())

async def _evaluate_asset_lifecycle():
    async with SessionLocal() as db:return await evaluate_asset_lifecycle(db)

@celery.task(name="dispatch_due_schedules")
def dispatch_due_schedules():return asyncio.run(_dispatch_due())

async def _dispatch_due():
    now=datetime.now(timezone.utc)
    queued_scans:list[tuple[str,str]]=[];queued_reports:list[tuple[str,str]]=[]
    async with SessionLocal() as db:
        scans=(await db.execute(select(ScanSchedule).where(ScanSchedule.enabled.is_(True),ScanSchedule.next_run_at<=now))).scalars().all()
        for schedule in scans:
            scope=ScanJob.vrf_id.is_(None) if schedule.vrf_id is None else ScanJob.vrf_id==schedule.vrf_id
            active=await db.scalar(select(ScanJob.id).where(ScanJob.target==schedule.target,scope,ScanJob.status.in_(["queued","running"])).limit(1))
            if not active:
                job=ScanJob(target=schedule.target,profile_id=schedule.profile_id,credential_id=schedule.credential_id,vrf_id=schedule.vrf_id,created_by=schedule.created_by);db.add(job);await db.flush();queued_scans.append((schedule.id,job.id))
            schedule.last_run_at=now;schedule.next_run_at=now+timedelta(minutes=schedule.interval_minutes)
        reports=(await db.execute(select(ReportSchedule).where(ReportSchedule.enabled.is_(True),ReportSchedule.next_run_at<=now))).scalars().all()
        for schedule in reports:
            queued_reports.append((schedule.id,schedule.id));schedule.last_run_at=now;schedule.next_run_at=now+timedelta(minutes=schedule.interval_minutes)
        await db.commit()
    failures=[]
    for schedule_id,job_id in queued_scans:
        try:execute_scan.apply_async(args=[job_id],queue="scanner",retry=False)
        except Exception as exc:failures.append(("scan",schedule_id,job_id,str(exc)));logger.exception("scheduled_scan_enqueue_failed",extra={"schedule_id":schedule_id,"job_id":job_id})
    for schedule_id,_ in queued_reports:
        try:send_scheduled_report.apply_async(args=[schedule_id],retry=False)
        except Exception as exc:failures.append(("report",schedule_id,None,str(exc)));logger.exception("scheduled_report_enqueue_failed",extra={"schedule_id":schedule_id})
    if failures:
        retry_at=now+timedelta(minutes=5)
        async with SessionLocal() as db:
            for kind,schedule_id,job_id,error in failures:
                schedule=await db.get(ScanSchedule if kind=="scan" else ReportSchedule,schedule_id)
                if schedule:schedule.next_run_at=retry_at
                if job_id:
                    job=await db.get(ScanJob,job_id)
                    if job:job.status="failed";job.error=f"Mise en file impossible: {error}"[:2000];job.finished_at=datetime.now(timezone.utc)
            await db.commit()
    return {"scans":len(queued_scans),"reports":len(queued_reports),"failures":len(failures)}

@celery.task(name="send_scheduled_report",autoretry_for=(Exception,),retry_backoff=True,retry_jitter=True,max_retries=3)
def send_scheduled_report(schedule_id:str):return asyncio.run(_send_scheduled_report(schedule_id))

async def _send_scheduled_report(schedule_id:str):
    import smtplib
    from email.message import EmailMessage
    from app.api.router import REPORT_LABELS,build_report,report_pdf
    async with SessionLocal() as db:
        schedule=await db.get(ReportSchedule,schedule_id)
        if not schedule or not schedule.enabled:return
        if not settings.smtp_host:raise RuntimeError("SMTP non configuré")
        if schedule.sender not in settings.smtp_sender_list:raise RuntimeError("Expéditeur du rapport planifié non autorisé")
        filename,content=await build_report(schedule.report_type,db);msg=EmailMessage();msg["From"]=schedule.sender;msg["To"]=", ".join(schedule.recipients);msg["Subject"]=f"NetScope — {REPORT_LABELS[schedule.report_type]}";msg.set_content("Rapport NetScope planifié en pièce jointe.")
        if schedule.format=="pdf":filename=filename.removesuffix(".csv")+".pdf";msg.add_attachment(report_pdf(schedule.report_type,content),maintype="application",subtype="pdf",filename=filename)
        else:msg.add_attachment(content.encode("utf-8-sig"),maintype="text",subtype="csv",filename=filename)
        def send():
            cls=smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
            with cls(settings.smtp_host,settings.smtp_port,timeout=settings.smtp_timeout) as client:
                if settings.smtp_use_tls and not settings.smtp_use_ssl:client.starttls()
                if settings.smtp_username:client.login(settings.smtp_username,settings.smtp_password)
                client.send_message(msg)
        await asyncio.to_thread(send)
