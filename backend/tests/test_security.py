import jwt
from types import SimpleNamespace
from app.core.config import settings
from app.core.security import create_token

def test_token_contains_security_claims():
    token=create_token(SimpleNamespace(id="user-1",role=SimpleNamespace(value="admin")))
    payload=jwt.decode(token,settings.secret_key,algorithms=["HS256"],issuer="netscope",audience="netscope-api")
    assert payload["sub"]=="user-1"
    assert payload["jti"]
    assert payload["iat"]<payload["exp"]
