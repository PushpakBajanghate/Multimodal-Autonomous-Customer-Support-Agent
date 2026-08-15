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
    POSTGRES_PORT: int = Field(default=5432)

    # Redis configurations
    REDIS_HOST: str = Field(default="127.0.0.1")
    REDIS_PORT: int = Field(default=6379)

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file="../.env",  # search root env
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
