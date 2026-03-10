"""
Configuration management for the Hospital AI Call Agent.
Reads all secrets and config from environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Gemini Hospital AI Call Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Google / Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_API_KEY: str = ""  # Optional alias; if set, use for new integrations
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_REGION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_LIVE_MODEL: str = "gemini-2.0-flash-live-001"

    # Exotel
    EXOTEL_ACCOUNT_SID: str = ""
    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""
    EXOTEL_PHONE_NUMBER: str = ""

    # Database
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    # Hospital / Phone Config
    HOSPITAL_NAME: str = "ABC Hospital"
    HOSPITAL_PHONE: str = "+1-800-ABC-HOSP"
    RECEPTIONIST_PHONE: str = "+1-800-ABC-RECV"
    DOCTOR_PHONE_NUMBER: str = ""      # Destination for non-emergency doctor transfers
    EMERGENCY_PHONE_NUMBER: str = ""   # Destination for emergency transfers (e.g. 911 or local ER)

    # Vapi
    VAPI_API_KEY: str = ""

    # Security
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    API_KEY_HEADER: str = "X-API-Key"

    # Supported Languages
    SUPPORTED_LANGUAGES: list = ["en-US", "hi-IN", "ta-IN"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
