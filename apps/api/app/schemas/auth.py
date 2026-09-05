from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OnboardingRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    preferences: list[str] = Field(default_factory=list, max_length=20)
    location_permission: str = Field(pattern="^(denied|while_using|always)$")


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    preferences: list[str]
    location_permission: str
    onboarding_complete: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
