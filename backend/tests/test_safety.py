import pytest
from fastapi import HTTPException
from app.services.safety import validate_target


def test_private_target_is_normalized(): assert validate_target("10.0.0.9/24")=="10.0.0.0/24"
@pytest.mark.parametrize("target",["0.0.0.0/0","127.0.0.1/32","224.0.0.0/4","not-a-network"])
def test_unsafe_target_rejected(target):
    with pytest.raises(HTTPException): validate_target(target)


def test_public_requires_confirmation():
    with pytest.raises(HTTPException): validate_target("8.8.8.8")
    assert validate_target("8.8.8.8",confirm_public=True)=="8.8.8.8/32"
