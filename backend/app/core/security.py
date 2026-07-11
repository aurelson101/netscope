from datetime import datetime, timedelta, timezone
import uuid
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db
from app.models import Role, User

password_hash = PasswordHash.recommended()
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def create_token(user: User) -> str:
    now=datetime.now(timezone.utc);expiry=now+timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub":user.id,"role":user.role.value,"iat":now,"exp":expiry,"jti":str(uuid.uuid4()),"iss":"netscope","aud":"netscope-api"},settings.secret_key,algorithm="HS256")


async def current_user(token: str = Depends(oauth2), db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload=jwt.decode(token,settings.secret_key,algorithms=["HS256"],issuer="netscope",audience="netscope-api",options={"require":["sub","iat","exp","jti"]})
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "Jeton invalide", headers={"WWW-Authenticate": "Bearer"}) from exc
    user = await db.get(User, payload.get("sub"))
    if not user or not user.active:
        raise HTTPException(401, "Utilisateur inactif")
    return user


def require(*roles: Role):
    async def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Permissions insuffisantes")
        return user
    return check
