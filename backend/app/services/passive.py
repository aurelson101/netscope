import hashlib,hmac,secrets
from datetime import datetime,timezone,timedelta
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models import PassiveConnector

def token_digest(token:str)->str:
    return hmac.new(settings.secret_key.encode(),token.encode(),hashlib.sha256).hexdigest()

def issue_connector_token(connector_id:str)->tuple[str,str]:
    token=f"{connector_id}.{secrets.token_urlsafe(32)}"
    return token,token_digest(token)

async def authenticate_connector(db:AsyncSession,token:str|None)->PassiveConnector:
    if not token or "." not in token:raise HTTPException(401,"Jeton de connecteur manquant ou invalide")
    connector_id=token.split(".",1)[0]
    connector=await db.get(PassiveConnector,connector_id)
    if not connector or not connector.enabled or not hmac.compare_digest(connector.token_hash,token_digest(token)):
        raise HTTPException(401,"Jeton de connecteur invalide")
    return connector

def validate_event_time(value:datetime|None)->datetime:
    now=datetime.now(timezone.utc)
    if value is None:return now
    if value.tzinfo is None:value=value.replace(tzinfo=timezone.utc)
    if value>now+timedelta(minutes=5) or value<now-timedelta(days=7):
        raise HTTPException(422,"La date d'observation est hors de la fenêtre autorisée")
    return value
