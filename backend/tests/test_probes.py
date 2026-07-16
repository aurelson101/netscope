from app.services.passive import token_digest
from app.services.probes import issue_probe_token,observation_in_scope

def test_probe_token_is_hashed_and_scoped_by_id():
    token,digest=issue_probe_token("probe-id")
    assert token.startswith("probe-id.") and digest==token_digest(token)

def test_probe_observation_must_remain_in_scan_scope():
    assert observation_in_scope("10.20.0.0/24","10.20.0.42")
    assert not observation_in_scope("10.20.0.0/24","10.21.0.42")
    assert not observation_in_scope("10.20.0.0/24","not-an-ip")
