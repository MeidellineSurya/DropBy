from fastapi import APIRouter

router = APIRouter()


@router.post("/location/ping")
def location_ping():
    """TODO: app/services/proximity.py — find nearby active Drops, compute
    reveal stage, persist drop_view_events, push drop.stage_update over WS."""
    raise NotImplementedError


@router.get("/{drop_id}")
def get_drop(drop_id: str):
    """TODO: return full Drop detail, gated by stage/discover_unlocked cache."""
    raise NotImplementedError
