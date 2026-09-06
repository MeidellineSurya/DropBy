import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_secrets() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, environment="production")


def test_production_accepts_a_strong_secret() -> None:
    configured = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="jwt-" + "a" * 40,
    )

    assert configured.environment == "production"
