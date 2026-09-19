import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


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

    # Operational Modes
    DEMO_MODE: bool = True
    AUTO_PROCESS_UPLOADS: bool = False  # Phase 1 only uploads without triggering auto extraction

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }


settings = Settings()

# Ensure directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
