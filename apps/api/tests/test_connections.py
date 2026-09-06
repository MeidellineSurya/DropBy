from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.connections import Connection, ConnectionStatus
from app.models.users import User
from app.services.connections import respond_request, send_request


def _user(user_id=None, display_name="Alex") -> User:
    return User(id=user_id or uuid4(), display_name=display_name, avatar_url=None)


def _stub_refresh_sets_created_at(db: MagicMock) -> None:
    """db.refresh() reloads server_default columns (created_at) from a real
    DB; against a MagicMock it's a no-op, so simulate that side effect."""
    db.refresh.side_effect = lambda obj: setattr(obj, "created_at", obj.created_at or datetime.now(timezone.utc))


def test_send_request_rejects_self() -> None:
    requester = _user()
    db = MagicMock(spec=Session)

    with pytest.raises(HTTPException) as exc_info:
        send_request(db, requester, requester.id)

    assert exc_info.value.status_code == 400
    db.add.assert_not_called()


def test_send_request_rejects_unknown_addressee() -> None:
    requester = _user()
    db = MagicMock(spec=Session)
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        send_request(db, requester, uuid4())

    assert exc_info.value.status_code == 404


def test_send_request_conflicts_when_already_pending() -> None:
    requester = _user()
    addressee_id = uuid4()
    existing = Connection(
        id=uuid4(), requester_id=requester.id, addressee_id=addressee_id, status=ConnectionStatus.pending
    )
    db = MagicMock(spec=Session)
    db.get.return_value = _user(addressee_id)
    db.scalar.return_value = existing

    with pytest.raises(HTTPException) as exc_info:
        send_request(db, requester, addressee_id)

    assert exc_info.value.status_code == 409
    db.commit.assert_not_called()


def test_send_request_creates_pending_connection() -> None:
    requester = _user()
    addressee = _user(display_name="Sam")
    db = MagicMock(spec=Session)
    db.get.side_effect = [addressee, addressee]
    db.scalar.return_value = None
    _stub_refresh_sets_created_at(db)

    result = send_request(db, requester, addressee.id)

    assert result.status == "pending"
    assert result.other_user.user_id == str(addressee.id)
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_send_request_reuses_row_after_a_decline() -> None:
    """Re-sending after a decline must update the existing row rather than
    insert a second one, since (requester_id, addressee_id) is unique."""
    requester = _user()
    addressee = _user(display_name="Sam")
    existing = Connection(
        id=uuid4(), requester_id=addressee.id, addressee_id=requester.id, status=ConnectionStatus.declined
    )
    db = MagicMock(spec=Session)
    db.get.side_effect = [addressee, addressee]
    db.scalar.return_value = existing
    _stub_refresh_sets_created_at(db)

    result = send_request(db, requester, addressee.id)

    assert result.status == "pending"
    assert existing.requester_id == requester.id
    assert existing.addressee_id == addressee.id
    db.add.assert_not_called()
    db.commit.assert_called_once()


def test_respond_request_rejects_non_addressee() -> None:
    user = _user()
    connection = Connection(
        id=uuid4(), requester_id=uuid4(), addressee_id=uuid4(), status=ConnectionStatus.pending
    )
    db = MagicMock(spec=Session)
    db.get.return_value = connection

    with pytest.raises(HTTPException) as exc_info:
        respond_request(db, user, connection.id, True)

    assert exc_info.value.status_code == 403


def test_respond_request_rejects_already_resolved() -> None:
    user = _user()
    connection = Connection(
        id=uuid4(), requester_id=uuid4(), addressee_id=user.id, status=ConnectionStatus.accepted
    )
    db = MagicMock(spec=Session)
    db.get.return_value = connection

    with pytest.raises(HTTPException) as exc_info:
        respond_request(db, user, connection.id, True)

    assert exc_info.value.status_code == 409


def test_respond_request_accepts() -> None:
    user = _user()
    requester = _user(display_name="Sam")
    connection = Connection(
        id=uuid4(), requester_id=requester.id, addressee_id=user.id, status=ConnectionStatus.pending
    )
    db = MagicMock(spec=Session)
    db.get.side_effect = [connection, requester]
    _stub_refresh_sets_created_at(db)

    result = respond_request(db, user, connection.id, True)

    assert result.status == "accepted"
    assert connection.responded_at is not None
    db.commit.assert_called_once()
