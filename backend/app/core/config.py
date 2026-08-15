from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multimodal Autonomous Customer Support Agent"
    API_V1_STR: str = "/api/v1"
    
    # Database configurations
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres_secure_password_change_me")
    POSTGRES_DB: str = Field(default="customer_support_db")
    POSTGRES_HOST: str = Field(default="127.0.0.1")
    POSTGRES_PORT: int = Field(default=5435)

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
    OPENAI_API_KEY: str | None = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    GEMINI_API_KEY: str | None = Field(default=None)
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash")
    LLM_TEMPERATURE: float = Field(default=0.1)

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file="../.env",  # search root env
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
