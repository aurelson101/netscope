from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.models import Base, ScanProfile, ScanSchedule
from app.workers import tasks

@pytest.mark.asyncio
async def test_scheduled_job_is_committed_before_celery_enqueue(tmp_path,monkeypatch):
    database=tmp_path/"scheduler.db";async_url=f"sqlite+aiosqlite:///{database}";sync_url=f"sqlite:///{database}"
    engine=create_async_engine(async_url);session_factory=async_sessionmaker(engine,expire_on_commit=False)
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        profile=ScanProfile(name="Test",modules=["icmp"],options={});db.add(profile);await db.flush()
        db.add(ScanSchedule(name="Toutes les heures",target="10.0.0.1",profile_id=profile.id,interval_minutes=60,enabled=True,next_run_at=datetime.now(timezone.utc)-timedelta(minutes=1)))
        await db.commit()
    monkeypatch.setattr(tasks,"SessionLocal",session_factory);observed=[]
    def enqueue(*,args,**kwargs):
        with create_engine(sync_url).connect() as connection:observed.append(connection.execute(text("SELECT count(*) FROM scan_jobs WHERE id=:id"),{"id":args[0]}).scalar_one())
    monkeypatch.setattr(tasks.execute_scan,"apply_async",enqueue)
    result=await tasks._dispatch_due()
    assert result=={"scans":1,"reports":0,"failures":0}
    assert observed==[1]
    await engine.dispose()
