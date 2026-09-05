from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.drops import Drop, DropStatus, DropViewStage
from app.models.groups import GroupStatus
from app.services.business_analytics import business_overview, drop_funnel


def test_drop_funnel_combines_view_and_squad_counts() -> None:
    db = MagicMock(spec=Session)
    db.execute.side_effect = [
        MagicMock(all=MagicMock(return_value=[
            (DropViewStage.detect, 10),
            (DropViewStage.discover, 3),
        ])),
        MagicMock(all=MagicMock(return_value=[
            (GroupStatus.forming, 2),
            (GroupStatus.ready, 1),
        ])),
    ]
    drop = Drop(
        id=uuid4(),
        business_id=uuid4(),
        status=DropStatus.active,
        reserved_count=4,
        max_capacity_participants=12,
    )

    result = drop_funnel(db, drop)

    assert result.detect_count == 10
    assert result.revealed_count == 3
    assert result.squads_forming == 2
    assert result.squads_ready == 1
    assert result.squads_checked_in == 0
    assert result.reserved_count == 4
    assert result.max_capacity_participants == 12


def test_business_overview_defaults_missing_statuses_to_zero() -> None:
    db = MagicMock(spec=Session)
    db.execute.side_effect = [
        MagicMock(all=MagicMock(return_value=[(DropStatus.active, 2)])),
        MagicMock(one=MagicMock(return_value=(6, 20))),
    ]
    db.scalar.return_value = 15

    result = business_overview(db, uuid4())

    assert result.active_drops == 2
    assert result.draft_drops == 0
    assert result.scheduled_drops == 0
    assert result.total_reserved_participants == 6
    assert result.total_capacity_participants == 20
    assert result.distinct_viewers_last_7_days == 15
