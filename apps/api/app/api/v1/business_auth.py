from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_business, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.businesses import Business, BusinessStatus
from app.schemas.business_auth import (
    BusinessLoginRequest,
    BusinessRegisterRequest,
    BusinessResponse,
    BusinessTokenResponse,
)

router = APIRouter()


def _business_response(db: Session, business: Business) -> BusinessResponse:
    geom = cast(Business.location, Geometry(geometry_type="POINT", srid=4326))
    latitude, longitude = db.execute(
        select(func.ST_Y(geom), func.ST_X(geom)).where(Business.id == business.id)
    ).one()
    return BusinessResponse(
        id=str(business.id),
        name=business.name,
        category=business.category,
        description=business.description,
        address=business.address,
        owner_email=business.owner_email,
        venue_capacity=business.venue_capacity,
        verified=business.verified,
        status=business.status.value,
        latitude=float(latitude),
        longitude=float(longitude),
    )


@router.post(
    "/register",
    response_model=BusinessTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: BusinessRegisterRequest, db: Session = Depends(get_db)
) -> BusinessTokenResponse:
    owner_email = str(body.owner_email).lower()
    if db.scalar(select(Business.id).where(Business.owner_email == owner_email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")
    business = Business(
        name=body.name.strip(),
        category=body.category.value,
        description=body.description,
        location=WKTElement(f"POINT({body.longitude} {body.latitude})", srid=4326),
        address=body.address,
        owner_email=owner_email,
        password_hash=hash_password(body.password),
        venue_capacity=body.venue_capacity,
        phone=body.phone,
        verified=False,
        status=BusinessStatus.pending,
    )
    db.add(business)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Email is already registered"
        ) from exc
    db.refresh(business)
    return BusinessTokenResponse(
        access_token=create_access_token(str(business.id), audience="business"),
        business=_business_response(db, business),
    )


@router.post("/login", response_model=BusinessTokenResponse)
def login(
    body: BusinessLoginRequest, db: Session = Depends(get_db)
) -> BusinessTokenResponse:
    business = db.scalar(
        select(Business).where(Business.owner_email == str(body.owner_email).lower())
    )
    if business is None or not verify_password(body.password, business.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return BusinessTokenResponse(
        access_token=create_access_token(str(business.id), audience="business"),
        business=_business_response(db, business),
    )


@router.get("/me", response_model=BusinessResponse)
def me(
    business: Business = Depends(get_current_business), db: Session = Depends(get_db)
) -> BusinessResponse:
    return _business_response(db, business)
