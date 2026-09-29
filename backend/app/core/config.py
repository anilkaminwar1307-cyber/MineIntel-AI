import os
import secrets
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator


_DEFAULT_JWT_SENTINEL = "CHANGE_ME_INSECURE_DEFAULT_SENTINEL"


class Settings(BaseSettings):
    APP_NAME: str = "MineIntel"
    APP_TAGLINE: str = "Evidence Intelligence for Mining & Geological Operations"
    APP_ENV: str = "development"
    DEBUG: bool = True
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # Database: Defaults to SQLite in ./data for quick local execution, PostgreSQL in production
    DATABASE_URL: str = Field(
        default="sqlite:///./data/mineintel.db",
        description="Database connection URL. Can be PostgreSQL or SQLite."
    )

    # Storage paths
    DATA_DIR: str = "./data"
    UPLOAD_DIR: str = "./data/uploads"
    REPORT_DIR: str = "./data/reports"
    MAX_UPLOAD_SIZE_MB: int = 50

    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # AI Provider Configuration
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # JWT Authentication — NO hardcoded default; must be set in non-development environments
    JWT_SECRET_KEY: str = Field(
        default=_DEFAULT_JWT_SENTINEL,
        description="JWT HMAC secret — MUST be set via environment variable in non-development"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # Operational Modes — DEMO_MODE is False by default; enable only in .env.example / demo envs
    DEMO_MODE: bool = False
    AUTO_PROCESS_UPLOADS: bool = False  # Phase 1 only uploads without triggering auto extraction

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        """
        In non-development environments the JWT_SECRET_KEY MUST be explicitly set
        to a strong random value. Fail fast at startup if the sentinel is still present.
        """
        if self.APP_ENV != "development" and self.JWT_SECRET_KEY in (
            _DEFAULT_JWT_SENTINEL, "", "mineintel-secret-development-key-change-in-prod-32bytes"
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be set to a strong random value in non-development "
                "environments. Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        # In development mode, silently replace the sentinel with a per-boot random key
        # so tests can run without a configured secret.
        if self.JWT_SECRET_KEY == _DEFAULT_JWT_SENTINEL:
            object.__setattr__(self, "JWT_SECRET_KEY", secrets.token_hex(32))
        return self


settings = Settings()

# Ensure directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
