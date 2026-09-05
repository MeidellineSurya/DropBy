from fastapi import APIRouter

router = APIRouter()


@router.get("/drops/{drop_id}")
def drop_funnel(drop_id: str):
    """TODO: detect -> reveal -> redeem conversion from drop_view_events."""
    raise NotImplementedError
