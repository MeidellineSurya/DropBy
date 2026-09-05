from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
def login():
    """TODO: verify credentials, return a JWT access token."""
    raise NotImplementedError


@router.post("/register")
def register():
    """TODO: create a user, hash password, return a JWT access token."""
    raise NotImplementedError
