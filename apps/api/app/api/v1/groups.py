from fastapi import APIRouter

router = APIRouter()


@router.post("")
def create_group():
    """TODO: app/services/squad_state.py — create a forming Group for a Drop."""
    raise NotImplementedError


@router.get("/{group_id}")
def get_group(group_id: str):
    """TODO: return current Group state (for reconnect/resync)."""
    raise NotImplementedError


@router.post("/{group_id}/join")
def join_group(group_id: str):
    """TODO: add member, recompute status, broadcast group.state_update / group.ready."""
    raise NotImplementedError


@router.post("/{group_id}/checkin")
def checkin_group(group_id: str):
    """TODO: app/services/redemption.py verify venue QR, transition to checked_in."""
    raise NotImplementedError
