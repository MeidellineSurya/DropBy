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

    default_detect_radius_m: int = 700
    default_reveal_radius_m: int = 180
    default_discover_radius_m: int = 100
    # Check-in is a location claim, not a QR scan (see services/redemption.py) —
    # deliberately much tighter than the Reveal radius above, since "near
    # enough to see the offer" and "actually at the counter" need different
    # thresholds. 10m is close to the accuracy floor of consumer GPS in open
    # sky (~3-5m) — tighter than that starts rejecting genuine claims on
    # ordinary GPS drift, especially near buildings, rather than catching
    # abuse. See STATUS.md if false rejections turn out to be a problem.
    check_in_radius_m: int = 10

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
        secrets = {"JWT_SECRET": self.jwt_secret}
        for name, value in secrets.items():
            if (
                len(value) < 32
                or value.startswith("change-me")
                or value.startswith("replace-with")
            ):
                raise ValueError(f"{name} must be a strong production secret")
        return self


settings = Settings()
