from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.business_drops import _require_active_business
from app.models.businesses import Business, BusinessStatus
from app.schemas.business_drops import BusinessDropCreateRequest


def make_business(status: BusinessStatus) -> Business:
    return Business(
        id=uuid4(),
        name="Seoul Table",
        category="food_dining",
        owner_email="owner@example.com",
        password_hash="not-used",
        verified=status == BusinessStatus.active,
        status=status,
    )


def test_active_business_may_publish() -> None:
    _require_active_business(make_business(BusinessStatus.active))  # does not raise


@pytest.mark.parametrize("status", [BusinessStatus.pending, BusinessStatus.suspended])
def test_non_active_business_is_blocked_from_publishing(status: BusinessStatus) -> None:
    # Previously nothing checked BusinessStatus at all: registering was
    # enough to immediately publish a live, discoverable Drop.
    with pytest.raises(HTTPException) as exc_info:
        _require_active_business(make_business(status))
    assert exc_info.value.status_code == 403


def test_create_request_defaults_to_not_publishing() -> None:
    # A pending business can still stage drafts; publish=False must not
    # trigger the active-business check at all.
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    request = BusinessDropCreateRequest(
        title="Rooftop cinema",
        category="activity_entertainment",
        drop_type="solo",
        latitude=-37.8119,
        longitude=144.9674,
        max_capacity_participants=10,
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=4),
    )
    assert request.publish is False
