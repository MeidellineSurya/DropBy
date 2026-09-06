from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.services.notifications import find_users_to_notify_for_drop
from app.workers.tasks.notifications import _format_distance


def test_format_distance_rounds_to_nearest_50m() -> None:
    """Same nearest-50m rounding Detect uses in-app — avoids handing out a
    precise-enough distance to triangulate the venue from a notification."""
    assert _format_distance(0) == "50m"
    assert _format_distance(24) == "50m"
    assert _format_distance(475) == "500m"
    assert _format_distance(499) == "500m"


def test_format_distance_switches_to_km_past_the_threshold() -> None:
    assert _format_distance(1000) == "1.0km"
    assert _format_distance(2450) == "2.5km"


def test_find_users_to_notify_for_drop_has_no_radius_or_freshness_filter() -> None:
    """Discovery is notification-driven now — every user with a known
    location gets notified about every Drop, not just people already
    nearby with a fresh ping. See services/notifications.py."""
    db = MagicMock(spec=Session)
    expected = [(uuid4(), 120.5), (uuid4(), 4200.0)]
    db.execute.return_value.all.return_value = expected

    result = find_users_to_notify_for_drop(db, uuid4())

    assert result == expected
    db.execute.assert_called_once()
