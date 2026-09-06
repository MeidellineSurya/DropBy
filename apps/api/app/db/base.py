from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models here so Alembic's autogenerate can discover them via Base.metadata.
from app.models import (  # noqa: E402,F401
    businesses,
    connections,
    drops,
    gamification,
    groups,
    messages,
    notifications,
    redemption,
    users,
)
