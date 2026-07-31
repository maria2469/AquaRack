"""
AquaMind AI — single FastAPI application (SDD full system).

One project, one app package, one entrypoint. Mounts every router:
telemetry, digital twin/simulation (including OpenDC/CloudSim), water
model, memory engine, multi-agent AI decision system, fleet dashboard,
reports, and live agent-trace streaming.

Route precedence: the multi-agent router (agents_router) is included
before the legacy single-agent recommend router, so POST /api/v1/recommend
is served by the multi-agent Orchestrator. health (with dependency
checks) takes precedence over the plain health handler for the same reason.

The telemetry collector daemon (app.collector.run_collector) runs as a
background thread inside this same process, started on startup — so a
single `uvicorn app.main:app` command is enough to get real, continuously
updating telemetry + weather data. No separate `python -m
app.collector.run_collector` process is needed. The thread is a daemon
thread, so it's killed automatically when the main process exits; no
manual shutdown/cleanup is required.

FIX (CORS): the previous allow_origins list only contained the production
Vercel domain (https://aqua-rack.vercel.app) and localhost. Vercel
preview/branch deployments get a per-branch generated URL of the form
aqua-rack-git-<branch>-<team>.vercel.app, which is what was actually
calling the API and getting blocked (no Access-Control-Allow-Origin header
-> every request failed before reaching route handlers). Added
allow_origin_regex to match any preview deployment for this project, plus
kept the explicit list for clarity/back-compat.
"""
import logging
import os
import threading

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.migrate import run_migrations
from app.routers import (
    agents_router,
    fleet_dashboard,
    fleet_telemetry,
    health,
    simulate_opendc,
    water_model_only,
    telemetry,
    simulate,
    recommend,
    memory,
    dashboard,
    reports,
    agent_trace,
    enterprise_api,
)
from app.mcp import server as mcp_server
from app.collector.run_collector import run as run_collector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler("aquamind.log"), logging.StreamHandler()],
)
logger = logging.getLogger("aquamind")

app = FastAPI(
    title="AquaRack",
    version="2.0.0",
    description=(
        "Digital twin of an AI data centre: telemetry ingestion, digital "
        "twin/simulation, water & cooling model, RAG memory engine, and a "
        "multi-agent AI decision system over CockroachDB Managed MCP, CockroachDB "
        "Vector Indexing, and Ollama (Llama 3.1 / Qwen2.5)."
    ),
)

# FIX: regex covers any Vercel preview/branch deployment for this project
# (e.g. https://aqua-rack-git-main-marias-projects-76dd7319.vercel.app),
# not just the single production URL. Adjust the team/project slug pattern
# below if your Vercel team or project name ever changes.
ALLOWED_ORIGIN_REGEX = r"^https://aqua-rack(-git-[a-z0-9\-]+)?(-[a-z0-9]+)?\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://aqua-rack.vercel.app",
    ],
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def optional_bearer_auth(request: Request, call_next):
    """Optional local API token. Disabled unless API_TOKEN is set."""
    if settings.API_TOKEN and request.url.path.startswith("/api/"):
        auth = request.headers.get("authorization", "")
        if auth != f"Bearer {settings.API_TOKEN}":
            return JSONResponse(
                status_code=401,
                content={
                    "type": "about:blank",
                    "title": "Unauthorized",
                    "status": 401,
                    "detail": "Missing or invalid bearer token",
                    "instance": str(request.url),
                },
            )
    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def rfc7807_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": exc.detail if isinstance(exc.detail, str) else "Error",
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url),
        },
    )


# Module-level handle to the collector thread. Kept as a reference mainly
# for introspection/debugging (e.g. checking .is_alive() from a shell);
# not required for shutdown since the thread is a daemon thread.
_collector_thread: threading.Thread | None = None


@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()
    from app.database import IS_COCKROACHDB
    logger.info(
        "AquaRack started. DB=%s (CockroachDB=%s) Ollama enabled=%s (model=%s)",
        settings.DATABASE_URL, IS_COCKROACHDB, settings.OLLAMA_ENABLED, settings.OLLAMA_MODEL,
    )

    # Start the telemetry collector daemon in-process as a background
    # thread, so a single uvicorn process produces real, continuously
    # updating telemetry + weather data without a second terminal/process.
    # daemon=True means this thread never blocks process exit.
    global _collector_thread
    _collector_thread = threading.Thread(
        target=run_collector,
        name="telemetry-collector",
        daemon=True,
    )
    _collector_thread.start()
    logger.info("Telemetry collector started as background thread (in-process, no separate daemon needed).")


# Enterprise and MCP routers
app.include_router(enterprise_api.router)
app.include_router(mcp_server.router)

# Multi-agent / fleet / simulation routers first so they take precedence
# on shared paths (notably POST /api/v1/recommend, GET /api/v1/health).
app.include_router(agents_router.router)
app.include_router(fleet_dashboard.router)
app.include_router(fleet_telemetry.router)
app.include_router(simulate_opendc.router)
app.include_router(water_model_only.router)
app.include_router(health.router)

# Core routers.
app.include_router(telemetry.router)
app.include_router(simulate.router)
app.include_router(recommend.router)
app.include_router(memory.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(agent_trace.router)


# --- Serve the dashboard (no Node/build step required) ---
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
if os.path.isdir(DASHBOARD_DIR):
    app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))