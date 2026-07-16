from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models import Alert, Asset, AssetArchive, AssetHistory, AssetStatus, Evidence


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def open_alert(db: AsyncSession, *, fingerprint: str, kind: str, severity: str, title: str, message: str, asset_id: str | None = None, details: dict | None = None, observed_at: datetime | None = None) -> Alert:
    timestamp = observed_at or utcnow()
    alert = await db.scalar(select(Alert).where(Alert.fingerprint == fingerprint))
    if alert:
        alert.last_seen = timestamp
        alert.message = message
        alert.details = details or alert.details
        if alert.status == "resolved":
            alert.status = "open"; alert.first_seen = timestamp; alert.resolved_at = None; alert.acknowledged_at = None; alert.acknowledged_by = None
        return alert
    alert = Alert(fingerprint=fingerprint,kind=kind,severity=severity,title=title,message=message,asset_id=asset_id,details=details or {},first_seen=timestamp,last_seen=timestamp)
    db.add(alert)
    return alert


async def resolve_alert(db: AsyncSession, fingerprint: str, resolved_at: datetime | None = None) -> bool:
    alert = await db.scalar(select(Alert).where(Alert.fingerprint == fingerprint, Alert.status != "resolved"))
    if not alert:return False
    alert.status = "resolved"; alert.resolved_at = resolved_at or utcnow(); return True


async def evaluate_asset_lifecycle(db: AsyncSession, now: datetime | None = None) -> dict:
    timestamp = now or utcnow(); cutoff = timestamp - timedelta(minutes=settings.asset_offline_minutes)
    observed = exists(select(Evidence.id).where(Evidence.asset_id == Asset.id))
    active = ~exists(select(AssetArchive.asset_id).where(AssetArchive.asset_id == Asset.id))
    assets = (await db.execute(select(Asset).where(active,observed,Asset.status.in_([AssetStatus.online,AssetStatus.offline]),Asset.last_seen < cutoff))).scalars().all()
    newly_offline = 0
    for asset in assets:
        if asset.status == AssetStatus.online:
            newly_offline += 1
            asset.status = AssetStatus.offline
            db.add(AssetHistory(asset_id=asset.id,event_type="status_changed",old_value=AssetStatus.online.value,new_value=AssetStatus.offline.value))
        label = asset.hostname or asset.id
        await open_alert(db,fingerprint=f"asset_offline:{asset.id}",kind="asset_offline",severity="critical",title="Équipement hors ligne",message=f"{label} n'a pas été observé depuis plus de {settings.asset_offline_minutes} minutes.",asset_id=asset.id,details={"last_seen":asset.last_seen.isoformat(),"threshold_minutes":settings.asset_offline_minutes},observed_at=timestamp)
    retention_cutoff = timestamp - timedelta(days=settings.alert_retention_days)
    deleted = await db.execute(delete(Alert).where(Alert.status == "resolved",Alert.resolved_at < retention_cutoff))
    await db.commit()
    return {"offline":newly_offline,"evaluated_offline":len(assets),"deleted_alerts":deleted.rowcount,"cutoff":cutoff.isoformat()}
