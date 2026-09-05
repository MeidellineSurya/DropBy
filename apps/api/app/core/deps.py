from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.businesses import Business
from app.models.users import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _subject_for_audience(
    credentials: HTTPAuthorizationCredentials | None, expected_audience: str
) -> str:
    try:
        if credentials is None:
            raise ValueError("missing bearer token")
        payload = decode_access_token(credentials.credentials)
        if payload.get("aud", "user") != expected_audience:
            raise ValueError("token is not valid for this audience")
        subject = payload.get("sub")
        if subject is None:
            raise ValueError("missing subject")
        return subject
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    return _subject_for_audience(credentials, "user")


def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    try:
        user = db.get(User, user_id)
    except (TypeError, ValueError):
        user = None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    return user


def get_current_business_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    return _subject_for_audience(credentials, "business")


def get_current_business(
    business_id: str = Depends(get_current_business_id),
    db: Session = Depends(get_db),
) -> Business:
    try:
        business = db.get(Business, business_id)
    except (TypeError, ValueError):
        business = None
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Business no longer exists",
        )
    return business
