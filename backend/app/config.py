"""
Central configuration for AquaRack / RackPulse.
"""

import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# D:\Projects\RackPulse\backend\app\config.py -> parent -> app
#                                              -> parent -> backend
#                                              -> parent -> RackPulse (repo root)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    # Thermal overhead for cooling estimation
    PUE_THERMAL_OVERHEAD: float = 0.4


    # ==========================================================
    # WEATHER API / ENVIRONMENT SIMULATION
    # ==========================================================
    WEATHER_ENABLED: bool = False

    # Faisalabad default coordinates
    WEATHER_LAT: float = 31.4187
    WEATHER_LON: float = 73.0791

    WEATHER_REFRESH_SECONDS: int = 900



    # ==========================================================
    # OLLAMA
    # ==========================================================
    OLLAMA_ENABLED: bool = True

    OLLAMA_BASE_URL: str = (
        "http://localhost:11434"
    )

    OLLAMA_MODEL: str = "llama3.1"

    OLLAMA_EMBED_MODEL: str = (
        "nomic-embed-text"
    )

    OLLAMA_TIMEOUT_SECONDS: int = 60



    # ==========================================================
    # BEDROCK (Optional)
    # ==========================================================
    BEDROCK_ENABLED: bool = False

    AWS_REGION: str = "us-east-1"

    BEDROCK_EMBED_MODEL_ID: str = (
        "amazon.titan-embed-text-v2:0"
    )

    BEDROCK_TEXT_MODEL_ID: str = (
        "us.anthropic.claude-sonnet-5"
    )



    # ==========================================================
    # AMAZON S3
    # ==========================================================
    S3_ENABLED: bool = True

    S3_BUCKET: str = os.getenv(
        "S3_BUCKET",
        ""
    )

    S3_PREFIX: str = "cold"

    S3_LOCAL_FALLBACK_DIR: str = (
        "./s3_lake"
    )



    # ==========================================================
    # AWS LAMBDA
    # ==========================================================
    LAMBDA_RETIER_SCHEDULE: str = (
        "rate(1 hour)"
    )



    # ==========================================================
    # SECRETS MANAGER
    # ==========================================================
    SECRETS_MANAGER_ENABLED: bool = False

    SECRETS_MANAGER_SECRET_NAME: str = (
        "aquamind/config"
    )



    # ==========================================================
    # CLOUDWATCH
    # ==========================================================
    CLOUDWATCH_ENABLED: bool = False

    CLOUDWATCH_LOG_GROUP: str = (
        "/aquamind/reasoning"
    )

    CLOUDWATCH_LOG_STREAM: str = os.getenv(
        "AQUARACK_DEVICE_ID",
        "rack-01-primary",
    )



    # ==========================================================
    # COLLECTOR
    # ==========================================================
    DEVICE_ID: str = os.getenv(
        "AQUARACK_DEVICE_ID",
        "rack-01-primary",
    )

    POLL_INTERVAL_SECONDS: int = 5

    LOCAL_QUEUE_DB: str = (
        "./collector_queue.db"
    )



    # ==========================================================
    # REPORTS
    # ==========================================================
    REPORTS_DIR: str = (
        "./reports"
    )



# ==========================================================
# CREATE SETTINGS INSTANCE
# ==========================================================

settings = Settings()



# ==========================================================
# LOG CONFIGURATION
# ==========================================================

logger = logging.getLogger("aquamind")

logger.info(
    "Config loaded: BASE_DIR=%s env_file_exists=%s WEATHER_ENABLED=%s WEATHER_LAT=%s WEATHER_LON=%s",
    BASE_DIR,
    (BASE_DIR / ".env").exists(),
    settings.WEATHER_ENABLED,
    settings.WEATHER_LAT,
    settings.WEATHER_LON,
)



# ==========================================================
# CREATE REQUIRED DIRECTORIES
# ==========================================================

os.makedirs(
    settings.REPORTS_DIR,
    exist_ok=True
)

os.makedirs(
    settings.S3_LOCAL_FALLBACK_DIR,
    exist_ok=True
)

GROQ_ENABLED: bool = True

GROQ_API_KEY: str = os.getenv(
    "GROQ_API_KEY",
    ""
)

GROQ_MODEL: str = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

GROQ_TIMEOUT_SECONDS: int = 60