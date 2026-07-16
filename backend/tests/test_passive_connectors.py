from datetime import datetime,timedelta,timezone
import pytest
from fastapi import HTTPException
from app.services.passive import issue_connector_token,token_digest,validate_event_time

def test_connector_token_contains_lookup_id_and_is_hashed():
    token,digest=issue_connector_token("connector-id")
    assert token.startswith("connector-id.")
    assert digest==token_digest(token)
    assert token not in digest

def test_passive_event_rejects_future_timestamp():
    with pytest.raises(HTTPException) as error:validate_event_time(datetime.now(timezone.utc)+timedelta(minutes=6))
    assert error.value.status_code==422

def test_passive_event_accepts_recent_timestamp():
    value=datetime.now(timezone.utc)-timedelta(minutes=2)
    assert validate_event_time(value)==value
