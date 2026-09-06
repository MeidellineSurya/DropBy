from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.connections import Connection, ConnectionStatus
from app.models.users import User
from app.services.chat import list_messages, send_message


def _user(user_id=None) -> User:
    return User(id=user_id or uuid4(), display_name="Alex", avatar_url=None)


def _stub_refresh_sets_created_at(db: MagicMock) -> None:
    db.refresh.side_effect = lambda obj: setattr(obj, "created_at", obj.created_at or datetime.now(timezone.utc))


def test_send_message_rejects_non_participant() -> None:
    user = _user()
    connection = Connection(
        id=uuid4(), requester_id=uuid4(), addressee_id=uuid4(), status=ConnectionStatus.accepted
    )
    db = MagicMock(spec=Session)
    db.get.return_value = connection

    with pytest.raises(HTTPException) as exc_info:
        send_message(db, user, connection.id, "hey")

    assert exc_info.value.status_code == 403
    db.add.assert_not_called()


def test_send_message_rejects_when_not_yet_accepted() -> None:
    user = _user()
    connection = Connection(
        id=uuid4(), requester_id=user.id, addressee_id=uuid4(), status=ConnectionStatus.pending
    )
    db = MagicMock(spec=Session)
    db.get.return_value = connection

    with pytest.raises(HTTPException) as exc_info:
        send_message(db, user, connection.id, "hey")

    assert exc_info.value.status_code == 409


def test_send_message_rejects_empty_body() -> None:
    user = _user()
    connection = Connection(
        id=uuid4(), requester_id=user.id, addressee_id=uuid4(), status=ConnectionStatus.accepted
    )
    db = MagicMock(spec=Session)
    db.get.return_value = connection

    with pytest.raises(HTTPException) as exc_info:
        send_message(db, user, connection.id, "   ")

    assert exc_info.value.status_code == 422
    db.add.assert_not_called()


def test_send_message_creates_message_for_a_participant() -> None:
    user = _user()
    connection = Connection(
        id=uuid4(), requester_id=user.id, addressee_id=uuid4(), status=ConnectionStatus.accepted
    )
    db = MagicMock(spec=Session)
    db.get.return_value = connection
    _stub_refresh_sets_created_at(db)

    result = send_message(db, user, connection.id, "  hey there  ")

    assert result.body == "hey there"
    assert result.sender_id == str(user.id)
    assert result.connection_id == str(connection.id)
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_list_messages_rejects_non_participant() -> None:
    user = _user()
    connection = Connection(
        id=uuid4(), requester_id=uuid4(), addressee_id=uuid4(), status=ConnectionStatus.accepted
    )
    db = MagicMock(spec=Session)
    db.get.return_value = connection

    with pytest.raises(HTTPException) as exc_info:
        list_messages(db, user, connection.id)

    assert exc_info.value.status_code == 403
