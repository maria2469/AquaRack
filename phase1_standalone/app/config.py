"""
Central configuration for the Phase 1 monolith (SDD Section 19 — local
deployment; Section 17.1 — security defaults).

All values are overridable via environment variables / a local .env file
(excluded from version control, per Section 17.1). Nothing here requires
AWS or any paid service to be configured — Phase 1 must run with zero
mandatory cloud dependency (FR-1.11).
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- API / server ---
    API_HOST: str = "127.0.0.1"  # local-only binding by default (Section 17.1)
    API_PORT: int = 8000
    API_TOKEN: str = ""  # optional bearer token; disabled unless set

    # --- Database (single-node CockroachDB free tier in prod, SQLite locally) ---
    DATABASE_URL: str = "sqlite:///./aquamind_phase1.db"

    # --- Rack / Digital Twin defaults (Section 12.2) ---
    RACK_CAPACITY_KW: float = 5.0
    RACK_NODE_COUNT: int = 1

    # --- Water Model defaults (Section 13) ---
    DEFAULT_AMBIENT_TEMP_C: float = 24.0
    DEFAULT_HUMIDITY_PCT: float = 55.0
    PUE_THERMAL_OVERHEAD: float = 0.4

    # --- Bedrock (optional — Section 16 / FR-1.11) ---
    BEDROCK_ENABLED: bool = False
    AWS_REGION: str = "us-east-1"
    BEDROCK_EMBED_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    BEDROCK_TEXT_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"

    # --- Collector (Section 14) ---
    DEVICE_ID: str = os.environ.get("AQUAMIND_DEVICE_ID", "laptop-local-01")
    POLL_INTERVAL_SECONDS: int = 5
    LOCAL_QUEUE_DB: str = "./collector_queue.db"

    # --- Reporting (Section 10.1) ---
    REPORTS_DIR: str = "./reports"


settings = Settings()

# Ensure the reports directory exists so /api/v1/reports/daily?format=pdf
# can always write its output file.
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
