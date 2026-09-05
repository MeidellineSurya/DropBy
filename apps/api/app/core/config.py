from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+psycopg://dropby:dropby@localhost:5432/dropby"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    qr_signing_secret: str = "change-me-too"
    fcm_credentials_json_path: str = ""

    default_detect_radius_m: int = 700
    default_reveal_radius_m: int = 180
    default_discover_radius_m: int = 100

    @model_validator(mode="after")
    def reject_unsafe_production_secrets(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        secrets = {
            "JWT_SECRET": self.jwt_secret,
            "QR_SIGNING_SECRET": self.qr_signing_secret,
        }
        for name, value in secrets.items():
            if (
                len(value) < 32
                or value.startswith("change-me")
                or value.startswith("replace-with")
            ):
                raise ValueError(f"{name} must be a strong production secret")
        if self.jwt_secret == self.qr_signing_secret:
            raise ValueError("JWT_SECRET and QR_SIGNING_SECRET must be different")
        return self


settings = Settings()
