"""
Central configuration for AquaRack.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
    DATABASE_URL: str = "cockroachdb://root@localhost:26257/aquarack?sslmode=disable"

    # ==========================================================
    # DIGITAL TWIN
    # ==========================================================
    RACK_CAPACITY_KW: float = 5.0
    RACK_NODE_COUNT: int = 1

    DEFAULT_AMBIENT_TEMP_C: float = 24.0
    DEFAULT_HUMIDITY_PCT: float = 55.0
    PUE_THERMAL_OVERHEAD: float = 0.4

    # ==========================================================
    # OLLAMA
    # ==========================================================
    OLLAMA_ENABLED: bool = True
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Recommended:
    OLLAMA_MODEL: str = "llama3.1"

    # Embeddings
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    OLLAMA_TIMEOUT_SECONDS: int = 60

    # ==========================================================
    # BEDROCK (Optional)
    # ==========================================================
    BEDROCK_ENABLED: bool = False

    AWS_REGION: str = "us-east-1"

    BEDROCK_EMBED_MODEL_ID: str = "amazon.titan-embed-text-v2:0"

    BEDROCK_TEXT_MODEL_ID: str = "us.anthropic.claude-sonnet-5"

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
    # SECRETS MANAGER
    # ==========================================================
    # Leave disabled unless you actually created a Secret.
    SECRETS_MANAGER_ENABLED: bool = False

    SECRETS_MANAGER_SECRET_NAME: str = "aquamind/config"

    # ==========================================================
    # CLOUDWATCH
    # ==========================================================
    CLOUDWATCH_ENABLED: bool = True

    CLOUDWATCH_LOG_GROUP: str = "/aquamind/reasoning"

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

    LOCAL_QUEUE_DB: str = "./collector_queue.db"

    # ==========================================================
    # REPORTS
    # ==========================================================
    REPORTS_DIR: str = "./reports"


settings = Settings()

os.makedirs(settings.REPORTS_DIR, exist_ok=True)