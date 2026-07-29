import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.routers import telemetry, simulate, recommend, memory, dashboard, reports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler("aquamind.log"), logging.StreamHandler()],
)
logger = logging.getLogger("aquamind")

app = FastAPI(
    title="AquaMind AI — Phase 1 (Standalone Laptop Digital Twin)",
    version="1.0.0",
    description="FastAPI monolith: telemetry ingestion, digital twin, water model, "
    "memory engine (RAG), and AI decision agent.",
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
    """Optional local API token (SDD Section 17.1). Disabled unless API_TOKEN is set."""
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
    """RFC 7807 problem+json error model (SDD Section 10.3)."""
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
    logger.info("AquaMind AI Phase 1 started. DB=%s", settings.DATABASE_URL)


app.include_router(telemetry.router)
app.include_router(simulate.router)
app.include_router(recommend.router)
app.include_router(memory.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "phase": 1}


# --- Serve the local dashboard (no Node/build step required) ---
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
if os.path.isdir(DASHBOARD_DIR):
    app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))
