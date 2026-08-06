"""
Central configuration for AquaRack / RackPulse.
"""

import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    API_PORT: int = 8000
    API_TOKEN: str = ""

    # ==========================================================
    # DATABASE
    # ==========================================================
    DATABASE_URL: str = (
        "cockroachdb://root@localhost:26257/aquarack?sslmode=disable"
    )

    # ==========================================================
    # DIGITAL TWIN
    # ==========================================================
    RACK_CAPACITY_KW: float = 5.0
    RACK_NODE_COUNT: int = 1

    DEFAULT_AMBIENT_TEMP_C: float = 24.0
    DEFAULT_HUMIDITY_PCT: float = 55.0

    PUE_THERMAL_OVERHEAD: float = 0.4

    # ==========================================================
    # WEATHER API / ENVIRONMENT SIMULATION
    # ==========================================================
    WEATHER_ENABLED: bool = False
    WEATHER_LAT: float = 31.4187
    WEATHER_LON: float = 73.0791
    WEATHER_REFRESH_SECONDS: int = 900

    # ==========================================================
    # OLLAMA (PRIMARY reasoning agent - Qwen)
    # ==========================================================
    OLLAMA_ENABLED: bool = True
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5")
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT_SECONDS: int = 180

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
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_PREFIX: str = "cold"
    S3_LOCAL_FALLBACK_DIR: str = "./s3_lake"

    # ==========================================================
    # AWS LAMBDA
    # ==========================================================
    LAMBDA_RETIER_SCHEDULE: str = "rate(1 hour)"

    # ==========================================================

    # ==========================================================
    # COLLECTOR
    # ==========================================================
    DEVICE_ID: str = os.getenv("AQUARACK_DEVICE_ID", "rack-01-primary")
    POLL_INTERVAL_SECONDS: int = 5
    LOCAL_QUEUE_DB: str = "./collector_queue.db"

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
# CREATE REQUIRED DIRECTORIES
# ==========================================================

os.makedirs(settings.REPORTS_DIR, exist_ok=True)
os.makedirs(settings.S3_LOCAL_FALLBACK_DIR, exist_ok=True)