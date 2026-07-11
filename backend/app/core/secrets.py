import base64
import hashlib
import json
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.master_encryption_key.encode()).digest())
    return Fernet(key)


def encrypt_secret(value: dict) -> str:
    return _fernet().encrypt(json.dumps(value).encode()).decode()


def decrypt_secret(value: str) -> dict:
    try:
        return json.loads(_fernet().decrypt(value.encode()))
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Impossible de déchiffrer l'identifiant") from exc
