from uuid import uuid4

from app.core.security import hash_password, verify_password
from app.schemas.groups import GroupCreateRequest


def test_password_hash_supports_long_unicode_passwords() -> None:
    password = "dropby-" + "🌏" * 40
    hashed = hash_password(password)

    assert hashed.startswith("$bcrypt-sha256$")
    assert verify_password(password, hashed)
    assert not verify_password(password + "x", hashed)


def test_squads_are_open_to_nearby_users_by_default() -> None:
    drop_id = uuid4()

    request = GroupCreateRequest(drop_id=drop_id)

    assert request.drop_id == drop_id
    assert request.open_to_nearby is True
