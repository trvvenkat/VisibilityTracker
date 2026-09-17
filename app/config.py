import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Visibility Check Tracker"
    DEBUG: bool = False

    # Browser automation settings
    BROWSER_HEADLESS: bool = False
    NAVIGATION_TIMEOUT: int = 30000  # ms
    SEARCH_TIMEOUT: int = 30000  # ms
    DEFAULT_TOP_N: int = 3

    # Platform base URLs
    AMAZON_BASE_URL: str = "https://www.amazon.in"
    FLIPKART_BASE_URL: str = "https://www.flipkart.com"

    # Scraper behavior
    DELAY_BETWEEN_KEYWORDS: float = 2.0  # seconds delay to reduce bot-detection triggers

    # Authentication settings
    AUTH_USERNAME: str = "admin"
    AUTH_PASSWORD: str = "tracker@2026"
    SECRET_KEY: str = "visibility-tracker-secure-secret-2026"
    SESSION_COOKIE_NAME: str = "vt_session"
    SESSION_MAX_AGE_SECS: int = 7 * 24 * 3600  # 7 days

    # Remote access / Tunnel settings (ngrok)
    NGROK_API_URL: str = "http://localhost:4040"

    # Storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    JOBS_DIR: Path = DATA_DIR / "jobs"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure required runtime directories exist
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
settings.JOBS_DIR.mkdir(parents=True, exist_ok=True)
