"""Core configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Talking BI"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # Anthropic / OpenAI / Groq
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""  # for Whisper
    GROQ_API_KEY: str = ""

    # ElevenLabs TTS
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./talking_bi.db"
    # For PostgreSQL: postgresql+asyncpg://user:pass@localhost/talking_bi
    # For MySQL: mysql+aiomysql://user:pass@localhost/talking_bi

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # External Data Sources
    # SQL (user's own database for analytics)
    ANALYTICS_DB_URL: Optional[str] = None  # e.g. mysql+aiomysql://user:pass@host/db

    # Power BI
    POWERBI_CLIENT_ID: Optional[str] = None
    POWERBI_CLIENT_SECRET: Optional[str] = None
    POWERBI_TENANT_ID: Optional[str] = None

    # Salesforce
    SALESFORCE_USERNAME: Optional[str] = None
    SALESFORCE_PASSWORD: Optional[str] = None
    SALESFORCE_SECURITY_TOKEN: Optional[str] = None

    # Shopify
    SHOPIFY_SHOP_URL: Optional[str] = None
    SHOPIFY_ACCESS_TOKEN: Optional[str] = None

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
