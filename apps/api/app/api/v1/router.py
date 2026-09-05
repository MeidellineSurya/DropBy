from fastapi import APIRouter

from app.api.v1 import (
    auth,
    business_analytics,
    business_auth,
    business_drops,
    devices,
    drops,
    gamification,
    groups,
    redemptions,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(drops.router, prefix="/drops", tags=["drops"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(business_auth.router, prefix="/business/auth", tags=["business"])
api_router.include_router(business_drops.router, prefix="/business/drops", tags=["business"])
api_router.include_router(business_analytics.router, prefix="/business/analytics", tags=["business"])
api_router.include_router(redemptions.router, prefix="/redemptions", tags=["redemptions"])
api_router.include_router(gamification.router, prefix="/gamification", tags=["gamification"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
