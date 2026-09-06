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

    fcm_credentials_json_path: str = ""

    # Signs each squad's check-in QR (see services/redemption.py) — a
    # separate secret from JWT_SECRET so a leak of one token domain doesn't
    # implicate the other.
    qr_signing_secret: str = "change-me-too"

    default_detect_radius_m: int = 700
    default_reveal_radius_m: int = 180
    default_discover_radius_m: int = 100

    # Comma-separated browser origins allowed to call the API (the business
    # dashboard, and any deployed equivalent). Defaults cover the dashboard's
    # Vite dev server both bare and via Docker Compose's port mapping.
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

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
