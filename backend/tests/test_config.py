import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_local_database_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = Settings(_env_file=None, DATABASE_URL=None)
    assert config.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///")


def test_database_url_takes_precedence():
    config = Settings(_env_file=None, DATABASE_URL="postgresql+psycopg://user:pass@db/app")
    assert config.SQLALCHEMY_DATABASE_URI == "postgresql+psycopg://user:pass@db/app"


def test_production_rejects_default_secrets(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("AGENT_SERVICE_SECRET", raising=False)
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            SECRET_KEY="super_secret_jwt_key_for_development_change_in_production",
        )


def test_production_accepts_non_default_secrets():
    config = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="a-real-production-secret",
        AGENT_SERVICE_SECRET="another-real-production-secret",
    )
    assert config.APP_ENV == "production"
