"""
Central configuration for AquaRack / RackPulse.
"""

import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    COHERE_ENABLED: bool = True
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    COHERE_EMBED_MODEL: str = "embed-english-v3.0"
        # ==========================================================
    # API
    # ==========================================================
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8001
    API_TOKEN: str = ""

    # ==========================================================
    # DATABASE
    # ==========================================================
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL must be set via environment variable")
        # Require SSL in production (no sslmode=disable allowed)
        if "sslmode=disable" in v:
            raise ValueError("SSL must be enabled for database connections in production")
        # Ensure sslrootcert is configured for cloud deployments
        if "sslrootcert=" not in v:
            # For cloud deployments, we'll let database.py handle the auto-configuration
            # But log a warning if it's missing
            import logging
            logging.warning("DATABASE_URL does not contain sslrootcert - will be auto-configured")
        return v

    # ==========================================================
    # DIGITAL TWIN
    # ==========================================================
    RACK_CAPACITY_KW: float = 5.0
    RACK_NODE_COUNT: int = 1
    FLEET_SIZE: int = 100  # 100 racks: 1 laptop + 99 digital twins
    RACK_PREFIX: str = "RACK"

    DEFAULT_AMBIENT_TEMP_C: float = 24.0
    DEFAULT_HUMIDITY_PCT: float = 55.0

    PUE_THERMAL_OVERHEAD: float = 0.4

    # ==========================================================
    # WEATHER API / ENVIRONMENT SIMULATION
    # ==========================================================
    WEATHER_ENABLED: bool = True  # Enable real weather from Open-Meteo
    WEATHER_LAT: float = 31.4187  # Update to your actual location latitude
    WEATHER_LON: float = 73.0791  # Update to your actual location longitude
    WEATHER_REFRESH_SECONDS: int = 900

    # ==========================================================
    # OLLAMA (PRIMARY reasoning agent - Qwen)
    # ==========================================================
    OLLAMA_ENABLED: bool = True
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")  # Better reasoning model
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT_SECONDS: int = 120  # 2 minutes for better interactive experience

    # ==========================================================
    # GROQ (FALLBACK reasoning agent, used only if Ollama fails)
    # ==========================================================
    GROQ_ENABLED: bool = True
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_TIMEOUT_SECONDS: int = 60
    EMBEDDING_DIM: int = 1024

    AWS_REGION: str = "us-east-1"

    # ==========================================================
    # AMAZON S3
    # ==========================================================
    S3_ENABLED: bool = True
    S3_BUCKET: str = os.getenv("S3_BUCKET", "rackpulse-cold-storage")
    S3_PREFIX: str = "cold"
    S3_LOCAL_FALLBACK_DIR: str = "./s3_lake"

    # ==========================================================
    # AWS LAMBDA
    # ==========================================================
    LAMBDA_RETIER_SCHEDULE: str = "rate(1 hour)"

    # ==========================================================
    # AMAZON CLOUDWATCH
    # ==========================================================
    CLOUDWATCH_ENABLED: bool = True

    # ==========================================================

    # ==========================================================
    # COLLECTOR
    # ==========================================================
    DEVICE_ID: str = os.getenv("AQUARACK_DEVICE_ID", "rack-01-primary")
    POLL_INTERVAL_SECONDS: int = 30  # Increased to 30 seconds to reduce API load and prevent timeouts
    COLLECTOR_ENABLED: bool = True  # Enabled for production telemetry collection

    # ==========================================================
    # REPORTS
    # ==========================================================
    REPORTS_DIR: str = "./reports"


# ==========================================================
# CREATE SETTINGS INSTANCE
# ==========================================================

settings = Settings()

# ==========================================================
# LOG CONFIGURATION
# ==========================================================

logger = logging.getLogger("aquamind")

logger.info(
    "Config loaded: BASE_DIR=%s env_file_exists=%s WEATHER_ENABLED=%s "
    "OLLAMA_ENABLED=%s GROQ_ENABLED=%s",
    BASE_DIR,
    (BASE_DIR / ".env").exists(),
    settings.WEATHER_ENABLED,
    settings.OLLAMA_ENABLED,
    settings.GROQ_ENABLED,
)

# ==========================================================
# LOG CONFIGURATION
# ==========================================================