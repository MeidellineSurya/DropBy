from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt_sha256 avoids bcrypt's 72-byte password limit while still allowing
# verification of any legacy bcrypt hashes already stored by the scaffold.
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str, expires_delta: timedelta | None = None, audience: str = "user"
) -> str:
    """`audience` ("user" or "business") keeps the two account spaces separate:
    a token minted for one can't be replayed against the other's dependencies,
    even if a UUID were ever somehow shared between the two tables."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire, "aud": audience}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Signature/expiry are verified here; callers that care about which
    account space issued the token check the returned "aud" claim themselves
    (see core/deps.py) rather than this function enforcing a single audience."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"verify_aud": False},
    )
