from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import get_current_business_id, get_current_user_id
from app.core.security import create_access_token, decode_access_token


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_business_token_defaults_to_business_audience() -> None:
    business_id = str(uuid4())
    token = create_access_token(business_id, audience="business")

    assert decode_access_token(token)["aud"] == "business"
    assert get_current_business_id(_bearer(token)) == business_id


def test_user_token_is_rejected_by_business_dependency() -> None:
    user_token = create_access_token(str(uuid4()))  # defaults to audience="user"

    with pytest.raises(HTTPException) as exc_info:
        get_current_business_id(_bearer(user_token))
    assert exc_info.value.status_code == 401


def test_business_token_is_rejected_by_user_dependency() -> None:
    business_token = create_access_token(str(uuid4()), audience="business")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(_bearer(business_token))
    assert exc_info.value.status_code == 401
