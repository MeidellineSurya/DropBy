from fastapi import APIRouter

router = APIRouter()


@router.post("/{redemption_id}/confirm")
def confirm_redemption(redemption_id: str):
    """TODO: business confirms headcount, completes Group, enqueues award_xp_for_redemption."""
    raise NotImplementedError
