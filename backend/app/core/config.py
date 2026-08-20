import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

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
    PROJECT_NAME: str = "Multimodal Autonomous Customer Support Agent"
    API_V1_STR: str = "/api/v1"
    
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

    # LLM Agent Configuration
    LLM_PROVIDER: str = Field(default="gemini")  # "gemini", "openai", or "mock"
    OPENAI_API_KEY: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    GEMINI_API_KEY: str | None = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    GEMINI_MODEL: str = Field(default="gemini-3.7-flash")
    LLM_TEMPERATURE: float = Field(default=0.2)

    # Human voice and outbound calling
    VOICE_PROVIDER: str = Field(default="sarvam")  # "sarvam", "elevenlabs", or "browser"
    PUBLIC_BASE_URL: str | None = Field(default=None)

    SARVAM_API_KEY: str | None = Field(default_factory=lambda: os.getenv("SARVAM_API_KEY"))
    SARVAM_TTS_URL: str = Field(default="https://api.sarvam.ai/text-to-speech")
    SARVAM_TTS_MODEL: str = Field(default="bulbul:v3")
    SARVAM_HINDI_SPEAKER: str = Field(default="anushka")
    SARVAM_ENGLISH_SPEAKER: str = Field(default="shubh")
    SARVAM_OUTPUT_CODEC: str = Field(default="wav")
    SARVAM_SAMPLE_RATE: int = Field(default=24000)

    ELEVENLABS_API_KEY: str | None = Field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY"))
    ELEVENLABS_TTS_URL: str = Field(default="https://api.elevenlabs.io/v1/text-to-speech")
    ELEVENLABS_VOICE_ID: str = Field(default="21m00Tcm4TlvDq8ikWAM")
    ELEVENLABS_MODEL_ID: str = Field(default="eleven_multilingual_v2")

    TWILIO_ACCOUNT_SID: str | None = Field(default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID"))
    TWILIO_AUTH_TOKEN: str | None = Field(default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN"))
    TWILIO_FROM_NUMBER: str | None = Field(default_factory=lambda: os.getenv("TWILIO_FROM_NUMBER"))

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=_ENV_PATHS,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

