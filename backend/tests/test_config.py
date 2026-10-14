import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_local_database_defaults_to_sqlite():
    config = Settings(_env_file=None)
    assert config.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///")


def test_database_url_takes_precedence():
    config = Settings(_env_file=None, DATABASE_URL="postgresql+psycopg://user:pass@db/app")
    assert config.SQLALCHEMY_DATABASE_URI == "postgresql+psycopg://user:pass@db/app"


def test_production_rejects_default_secrets():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, APP_ENV="production")


def test_production_accepts_non_default_secrets():
    config = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="a-real-production-secret",
        AGENT_SERVICE_SECRET="another-real-production-secret",
    )
    assert config.APP_ENV == "production"
