import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

# Determine project base directory and .env paths
_CURRENT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _CURRENT_DIR.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent

_ENV_PATHS = [
    _ROOT_DIR / ".env",
    _BACKEND_DIR / ".env",
    Path(".env"),
    Path("../.env")
]

class Settings(BaseSettings):
    APP_ENV: str = Field(default="development")
    PROJECT_NAME: str = "Multimodal Autonomous Customer Support Agent"
    API_V1_STR: str = "/api/v1"
    # Comma-separated browser origins allowed to call the API. Keep the
    # Vercel regex enabled for preview deployments and use CORS_ORIGINS for
    # the production/custom frontend domain.
    CORS_ORIGINS: str = ""
    CORS_ORIGIN_REGEX: str = r"https://([a-z0-9-]+\.)?vercel\.app"
    
    # Database configurations
    DATABASE_URL: str | None = Field(default=None)
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres_secure_password_change_me")
    POSTGRES_DB: str = Field(default="customer_support_db")
    POSTGRES_HOST: str = Field(default="127.0.0.1")
    POSTGRES_PORT: int = Field(default=5432)

    # Redis configurations
    REDIS_HOST: str = Field(default="127.0.0.1")
    REDIS_PORT: int = Field(default=6379)

    # Security & JWT Auth
    SECRET_KEY: str = Field(default="super_secret_jwt_key_for_development_change_in_production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)  # 24 hours
    AGENT_SERVICE_SECRET: str = Field(default="agent_internal_service_secret_key_2026")

    # LLM Agent Configuration & 4-Tier Resilience
    LLM_PROVIDER: str = Field(default="gemini")  # "gemini", "openai", or "mock"
    OPENAI_API_KEY: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    GEMINI_API_KEY: str | None = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash-lite")
    LLM_TEMPERATURE: float = Field(default=0.7)

    # 4-Tier LLM Architecture Configuration (Ultra-Fast Response & High Resilience)
    LLM_TIER1_MODEL: str = Field(default="gemini-3.5-flash-lite")
    LLM_TIER2_MODEL: str = Field(default="gemini-3.1-flash-lite")
    LLM_TIER3_MODEL: str = Field(default="gemini-3.6-flash")
    LLM_TIER1_TIMEOUT: float = Field(default=5.0)
    LLM_TIER2_TIMEOUT: float = Field(default=4.0)
    LLM_TIER3_TIMEOUT: float = Field(default=3.5)

    # Human voice and outbound calling
    VOICE_PROVIDER: str = Field(default="sarvam")  # "sarvam", "elevenlabs", or "browser"
    PUBLIC_BASE_URL: str | None = Field(default=None)

    SARVAM_API_KEY: str | None = Field(default_factory=lambda: os.getenv("SARVAM_API_KEY"))
    SARVAM_TTS_URL: str = Field(default="https://api.sarvam.ai/text-to-speech")
    SARVAM_TTS_MODEL: str = Field(default="bulbul:v3")
    SARVAM_HINDI_SPEAKER: str = Field(default="ritu")
    SARVAM_ENGLISH_SPEAKER: str = Field(default="shubh")
    SARVAM_OUTPUT_CODEC: str = Field(default="wav")
    SARVAM_SAMPLE_RATE: int = Field(default=24000)

    ELEVENLABS_API_KEY: str | None = Field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY"))
    ELEVENLABS_AGENT_ID: str | None = Field(default_factory=lambda: os.getenv("ELEVENLABS_AGENT_ID"))
    ELEVENLABS_TTS_URL: str = Field(default="https://api.elevenlabs.io/v1/text-to-speech")
    ELEVENLABS_VOICE_ID: str = Field(default="EXAVITQu4vr4xnSDxMaL")
    ELEVENLABS_MODEL_ID: str = Field(default="eleven_multilingual_v2")

    TWILIO_ACCOUNT_SID: str | None = Field(default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID"))
    TWILIO_AUTH_TOKEN: str | None = Field(default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN"))
    TWILIO_FROM_NUMBER: str | None = Field(default_factory=lambda: os.getenv("TWILIO_FROM_NUMBER"))

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # DATABASE_URL is the explicit override used by Docker Compose. Without
        # it, local development is intentionally zero-configuration SQLite.
        if self.DATABASE_URL and self.DATABASE_URL.strip():
            return self.DATABASE_URL
        return f"sqlite:///{(_BACKEND_DIR / 'macs.db').as_posix()}"

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.APP_ENV.lower() == "production":
            insecure_values = {
                "SECRET_KEY": "super_secret_jwt_key_for_development_change_in_production",
                "AGENT_SERVICE_SECRET": "agent_internal_service_secret_key_2026",
            }
            for field_name, default_value in insecure_values.items():
                if getattr(self, field_name) == default_value:
                    raise ValueError(
                        f"{field_name} must be changed when APP_ENV=production"
                    )
        return self

    model_config = SettingsConfigDict(
        env_file=_ENV_PATHS,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

