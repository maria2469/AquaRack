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
"""
import logging
import os

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
        "multi-agent AI decision system over CockroachDB and Amazon "
        "Bedrock (via LangChain)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()
    from app.database import IS_COCKROACHDB
    logger.info(
        "AquaRack started. DB=%s (CockroachDB=%s) Bedrock/LangChain enabled=%s",
        settings.DATABASE_URL, IS_COCKROACHDB, settings.BEDROCK_ENABLED,
    )


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
