"""
Central configuration for AquaMind AI (SDD Section 19 — deployment;
Section 17.1 — security defaults).

All values are overridable via environment variables / a local .env file
(excluded from version control, per Section 17.1).
"""
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- API / server ---
    API_HOST: str = "127.0.0.1"  # local-only binding by default (Section 17.1)
    API_PORT: int = 8000
    API_TOKEN: str = ""  # optional bearer token; disabled unless set

    # --- Database (SDD Tech Stack: CockroachDB) ---
    # Defaults to a local CockroachDB node (e.g. `cockroach start-single-node
    # --insecure` or the docker-compose `cockroachdb` service). Point
    # DATABASE_URL at CockroachDB Cloud / a secured cluster in production.
    # SQLite remains available as an explicit opt-out for offline dev
    # (set DATABASE_URL=sqlite:///./aquamind_phase1.db) but is no longer the
    # default, since the SDD tech stack calls for CockroachDB.
    DATABASE_URL: str = "cockroachdb://root@localhost:26257/aquamind?sslmode=disable"

    # --- Rack / Digital Twin defaults (Section 12.2) ---
    RACK_CAPACITY_KW: float = 5.0
    RACK_NODE_COUNT: int = 1

    # --- Water Model defaults (Section 13) ---
    DEFAULT_AMBIENT_TEMP_C: float = 24.0
    DEFAULT_HUMIDITY_PCT: float = 55.0
    PUE_THERMAL_OVERHEAD: float = 0.4

    # --- Bedrock (SDD Tech Stack: Amazon Bedrock reasoning, via LangChain) ---
    # Enabled by default per the SDD tech stack. Requires AWS credentials
    # with bedrock:InvokeModel access in AWS_REGION and model access
    # granted in the Bedrock console. If credentials are missing or a call
    # fails for any reason, every call site falls back automatically to
    # the deterministic local implementation (FR-1.11) — set
    # BEDROCK_ENABLED=false explicitly to skip Bedrock entirely (e.g. CI).
    BEDROCK_ENABLED: bool = True
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
