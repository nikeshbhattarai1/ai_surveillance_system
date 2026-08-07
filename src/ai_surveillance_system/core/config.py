from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # App
    APP_NAME: str = "AI Surveillance System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development",
                         "staging", "production"] = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(
        ...,
        description="POSTGRESQL connection string"
    )

    # JWT
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="JWT signing key."
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # File Storage
    UPLOAD_DIR: Path = Path("storage/uploads")
    FRAMES_DIR: Path = Path("storage/frames")
    MAX_UPLOAD_SIZE_MB: int = Field(default=500, ge=1, le=5000)

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # ML
    MODEL_PATH: Path = Path("models/violence_detection.pt")
    CONFIDENCE_THRESHOLD: float = Field(default=0.75, ge=0.0, le=1.0)

    # Notifications - Twilio (WhatsApp)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = ""
    ALERT_PHONE_NUMBER: str = ""

    # Notification - Email (SMTP)
    ALERT_EMAIL: str = ""
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = "" 

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Prevent common insecure secret keys.
        """
        weak_keys = {
            "change-me",
            "secret",
            "password",
            "123456789"
        }

        if v.lower() in weak_keys:
            raise ValueError(
                "SECRET_KEY is too weak"
            )
        return v

    @field_validator("UPLOAD_DIR", "FRAMES_DIR", mode="after")
    @classmethod
    def create_directories(cls, path: Path) -> Path:
        """
        Auto-create folder during startup time.
        """
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_settings() -> Settings:
    return Settings()
