from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_business, get_db
from app.models.businesses import Business
from app.models.drops import Drop
from app.schemas.business_analytics import BusinessOverviewResponse, DropFunnelResponse
from app.services.business_analytics import business_overview, drop_funnel

router = APIRouter()


@router.get("/overview", response_model=BusinessOverviewResponse)
def overview(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> BusinessOverviewResponse:
    return business_overview(db, business.id)


@router.get("/drops/{drop_id}", response_model=DropFunnelResponse)
def drop_funnel_route(
    drop_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> DropFunnelResponse:
    drop = db.scalar(
        select(Drop).where(Drop.id == drop_id, Drop.business_id == business.id)
    )
    if drop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Drop not found")
    return drop_funnel(db, drop)
