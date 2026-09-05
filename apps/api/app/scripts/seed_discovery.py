from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.businesses import Business, BusinessStatus
from app.models.drops import Drop, DropCategory, DropRarity, DropStatus, DropType
from app.models.users import User

DEMO_PREFERENCES = ["korean_bbq", "japanese_cuisine", "laser_tag"]


def seed() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "explorer@dropbyapp.com"))
        if user is None:
            user = db.scalar(select(User).where(User.email == "explorer@dropby.test"))
            if user is not None:
                user.email = "explorer@dropbyapp.com"
        if user is None:
            user = User(
                email="explorer@dropbyapp.com",
                password_hash=hash_password("dropby12345"),
                display_name="Test Explorer",
                preferences=DEMO_PREFERENCES,
                location_permission="while_using",
                onboarding_completed_at=datetime.now(timezone.utc),
            )
            db.add(user)
        elif user.preferences == ["food_dining", "activity_entertainment"]:
            user.preferences = DEMO_PREFERENCES

        business = db.scalar(
            select(Business).where(Business.owner_email == "venue@dropbyapp.com")
        )
        if business is None:
            business = db.scalar(
                select(Business).where(Business.owner_email == "venue@dropby.test")
            )
            if business is not None:
                business.owner_email = "venue@dropbyapp.com"
        if business is None:
            business = Business(
                name="Seoul Table",
                category="food_dining",
                location=WKTElement("POINT(144.9674 -37.8119)", srid=4326),
                address="200 Little Bourke Street, Melbourne VIC",
                owner_email="venue@dropbyapp.com",
                password_hash=hash_password("dropby12345"),
                verified=True,
                status=BusinessStatus.active,
            )
            db.add(business)
            db.flush()

        existing = db.scalar(
            select(Drop).where(Drop.title == "Rare Korean BBQ Drop")
        )
        if existing is None:
            db.add(
                Drop(
                    business_id=business.id,
                    title="Rare Korean BBQ Drop",
                    description="40% off the group dining menu",
                    category=DropCategory.food_dining,
                    interest_tag="korean_bbq",
                    rarity=DropRarity.rare,
                    drop_type=DropType.squad,
                    min_group_size=2,
                    max_group_size=4,
                    location=WKTElement("POINT(144.9674 -37.8119)", srid=4326),
                    max_capacity_participants=12,
                    starts_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                    ends_at=datetime.now(timezone.utc) + timedelta(hours=6),
                    status=DropStatus.active,
                )
            )
        else:
            existing.discover_radius_m = settings.default_discover_radius_m
            existing.interest_tag = "korean_bbq"
        db.commit()
    print("Seeded explorer@dropbyapp.com and a Melbourne discovery Drop")


if __name__ == "__main__":
    seed()
