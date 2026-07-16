import pytest
import asyncssh
from app.services.device_config import config_checksum,platform_policy,validate_configuration,validate_ssh_secret

def test_configuration_is_normalized_and_hashed():
    content=validate_configuration("hostname edge\r\ninterface Ethernet1\r\n description uplink\r\n")
    assert "\r" not in content and len(config_checksum(content))==64

def test_short_configuration_is_rejected():
    with pytest.raises(ValueError,match="incomplète"):validate_configuration("empty")

def test_fortios_restore_is_explicitly_disabled():
    assert platform_policy("fortios")["restore"] is None

def test_unknown_platform_is_rejected():
    with pytest.raises(ValueError,match="non prise en charge"):platform_policy("unknown")

def test_ssh_auth_requires_exactly_one_method():
    with pytest.raises(ValueError,match="soit"):validate_ssh_secret({"password":"x","private_key":"y","host_key":"z"})

def test_real_openssh_keys_are_accepted():
    key=asyncssh.generate_private_key("ssh-ed25519")
    validate_ssh_secret({"username":"backup","private_key":key.export_private_key().decode(),"host_key":key.export_public_key().decode()})
