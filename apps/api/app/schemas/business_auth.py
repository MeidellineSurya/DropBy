from pydantic import BaseModel, EmailStr, Field


class BusinessRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=60)
    owner_email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
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
    verified: bool
    status: str


class BusinessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    business: BusinessResponse
