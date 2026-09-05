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
    default_discover_radius_m: int = 60


settings = Settings()
