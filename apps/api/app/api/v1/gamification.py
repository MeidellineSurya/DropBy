from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.gamification import PowerupType
from app.models.users import User
from app.schemas.gamification import (
    ChoosePerkRequest,
    DropHistoryEntry,
    PerkResponse,
    RedeemPowerupRequest,
    RedeemPowerupResponse,
    UserStatsResponse,
    WeeklyChallengeResponse,
)
from app.services.gamification import (
    choose_perk,
    claim_weekly_challenge,
    get_drop_history,
    get_user_stats,
    get_weekly_challenge_status,
    redeem_powerup,
)
from app.ws.manager import publish
from ws_contracts.events import GroupStateUpdate

router = APIRouter()


@router.get("/me/stats", response_model=UserStatsResponse)
def my_stats(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserStatsResponse:
    """user_stats + badges (locked and unlocked) + powerup inventory + xp/level."""
    return get_user_stats(db, user)


@router.get("/me/history", response_model=list[DropHistoryEntry])
def my_history(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[DropHistoryEntry]:
    """Every Drop this user has completed, most recent first."""
    return get_drop_history(db, user)


@router.post("/powerups/{powerup_id}/redeem", response_model=RedeemPowerupResponse)
async def redeem(
    powerup_id: UUID,
    body: RedeemPowerupRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedeemPowerupResponse:
    powerup_type, details = await redeem_powerup(db, user, powerup_id, body.group_id)

    group = details.get("group")
    if group is not None:
        event = GroupStateUpdate(
            group_id=group.id,
            drop_id=group.drop_id,
            status=group.status.value,
            current_count=group.current_count,
            min_required=group.min_required,
            max_allowed=group.max_allowed,
            members=[member.model_dump(mode="json") for member in group.members],
            expires_at=group.expires_at,
        ).model_dump(mode="json")
        for topic in {f"ws:group:{group.id}", *(f"ws:user:{m.user_id}" for m in group.members)}:
            await publish(topic, event)

    return RedeemPowerupResponse(
        powerup_type=powerup_type,
        group=group,
        deadline=details.get("deadline"),
        boost_expires_at=details.get("boost_expires_at"),
    )


@router.get("/powerups/types")
def powerup_types() -> list[str]:
    """Reference list for clients building a redeem UI."""
    return [powerup.value for powerup in PowerupType]


@router.post("/perks/choose", response_model=PerkResponse)
def choose(
    body: ChoosePerkRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PerkResponse:
    """Spends one pending level-milestone perk choice (GET /me/stats reports
    pending_perk_choices)."""
    perk = choose_perk(db, user, body.type, body.category)
    return PerkResponse(milestone_level=perk.milestone_level, type=perk.type, category=perk.category)


@router.get("/challenges/weekly", response_model=WeeklyChallengeResponse)
def weekly_challenge(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> WeeklyChallengeResponse:
    """This week's rotating category challenge and your progress toward it."""
    return get_weekly_challenge_status(db, user)


@router.post("/challenges/weekly/claim", response_model=WeeklyChallengeResponse)
def claim(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> WeeklyChallengeResponse:
    """Claims this week's bonus XP once progress has reached the target."""
    return claim_weekly_challenge(db, user)
