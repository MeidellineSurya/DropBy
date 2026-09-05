from fastapi import APIRouter

router = APIRouter()


@router.post("")
def create_drop():
    """TODO: business creates a Drop (draft/scheduled) — offer, capacity, radius, timing, rarity."""
    raise NotImplementedError


@router.get("")
def list_business_drops():
    """TODO: list this business's Drops with status."""
    raise NotImplementedError


@router.post("/{drop_id}/cancel")
def cancel_drop(drop_id: str):
    """TODO: app/services/drop_lifecycle.py — cancel, cascade to in-flight groups."""
    raise NotImplementedError
