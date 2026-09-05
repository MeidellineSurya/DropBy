from pydantic import BaseModel, EmailStr, Field

from app.models.drops import DropCategory


class BusinessRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    # Same fixed set a business's own Drops are categorized under (the
    # dashboard's registration form already only offers these); previously a
    # free-text field, which let a business register with an arbitrary
    # category that would never match anything real.
    category: DropCategory
    owner_email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    # Declared once, here, not per Drop — see Business.venue_capacity and
    # services/drop_lifecycle.compute_rarity for why.
    venue_capacity: int = Field(gt=0, le=10_000)
    description: str | None = Field(default=None, max_length=2000)
    address: str | None = Field(default=None, max_length=250)
    phone: str | None = Field(default=None, max_length=40)


class BusinessLoginRequest(BaseModel):
    owner_email: EmailStr
    password: str


class BusinessResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str | None
    address: str | None
    owner_email: str
    venue_capacity: int
    verified: bool
    status: str


class BusinessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    business: BusinessResponse
