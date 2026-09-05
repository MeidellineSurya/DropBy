from fastapi import APIRouter

router = APIRouter()


@router.get("/me/stats")
def my_stats():
    """TODO: return user_stats + badges + xp/level."""
    raise NotImplementedError
