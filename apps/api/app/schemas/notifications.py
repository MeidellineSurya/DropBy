from pydantic import BaseModel


class RegisterDeviceRequest(BaseModel):
    fcm_token: str
    platform: str  # "ios" | "android" | "web"


class DeviceResponse(BaseModel):
    id: str
    platform: str
    active: bool
