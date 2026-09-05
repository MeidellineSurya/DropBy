from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.main import _business_topics, _user_topics
from app.models.businesses import Business
from app.models.users import User


def test_user_topics_none_for_unknown_user() -> None:
    db = MagicMock(spec=Session)
    db.get.return_value = None

    assert _user_topics(db, uuid4()) is None


def test_user_topics_include_active_group_memberships() -> None:
    db = MagicMock(spec=Session)
    user_id = uuid4()
    group_id = uuid4()
    db.get.return_value = User(id=user_id)
    db.scalars.return_value.all.return_value = [group_id]

    topics = _user_topics(db, user_id)

    assert topics == [f"ws:user:{user_id}", f"ws:group:{group_id}"]


def test_business_topics_none_for_unknown_business() -> None:
    db = MagicMock(spec=Session)
    db.get.return_value = None

    assert _business_topics(db, uuid4()) is None


def test_business_topics_include_live_drops() -> None:
    db = MagicMock(spec=Session)
    business_id = uuid4()
    drop_id = uuid4()
    db.get.return_value = Business(id=business_id)
    db.scalars.return_value.all.return_value = [drop_id]

    topics = _business_topics(db, business_id)

    assert topics == [f"ws:business:{business_id}", f"ws:drop:{drop_id}"]
