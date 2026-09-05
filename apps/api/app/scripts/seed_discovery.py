from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.businesses import Business, BusinessStatus
from app.models.drops import Drop, DropCategory, DropRarity, DropStatus, DropType
from app.models.users import User


def seed() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "explorer@dropby.test"))
        if user is None:
            db.add(
                User(
                    email="explorer@dropby.test",
                    password_hash=hash_password("dropby12345"),
                    display_name="Test Explorer",
                    preferences=["food_dining", "activity_entertainment"],
                    location_permission="while_using",
                    onboarding_completed_at=datetime.now(timezone.utc),
                )
            )

        business = db.scalar(
            select(Business).where(Business.owner_email == "venue@dropby.test")
        )
        if business is None:
            business = Business(
                name="Seoul Table",
                category="food_dining",
                location=WKTElement("POINT(144.9674 -37.8119)", srid=4326),
                address="200 Little Bourke Street, Melbourne VIC",
                owner_email="venue@dropby.test",
                password_hash=hash_password("dropby12345"),
                verified=True,
                status=BusinessStatus.active,
            )
            db.add(business)
            db.flush()

        existing = db.scalar(
            select(Drop.id).where(Drop.title == "Rare Korean BBQ Drop")
        )
        if existing is None:
            db.add(
                Drop(
                    business_id=business.id,
                    title="Rare Korean BBQ Drop",
                    description="40% off the group dining menu",
                    category=DropCategory.food_dining,
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
        db.commit()
    print("Seeded explorer@dropby.test and a Melbourne discovery Drop")


if __name__ == "__main__":
    seed()
