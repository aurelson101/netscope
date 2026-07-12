from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.security import require
from app.models import Role


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        (Role.admin, True),
        (Role.operator, True),
        (Role.viewer, False),
    ],
)
async def test_operator_permission_excludes_viewer(role: Role, allowed: bool):
    guard = require(Role.admin, Role.operator)
    user = SimpleNamespace(role=role)

    if allowed:
        assert await guard(user=user) is user
    else:
        with pytest.raises(HTTPException) as error:
            await guard(user=user)
        assert error.value.status_code == 403
        assert error.value.detail == "Permissions insuffisantes"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        (Role.admin, True),
        (Role.operator, False),
        (Role.viewer, False),
    ],
)
async def test_administrator_permission_is_exclusive(role: Role, allowed: bool):
    guard = require(Role.admin)
    user = SimpleNamespace(role=role)

    if allowed:
        assert await guard(user=user) is user
    else:
        with pytest.raises(HTTPException) as error:
            await guard(user=user)
        assert error.value.status_code == 403
