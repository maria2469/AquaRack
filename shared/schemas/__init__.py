"""
Shared schemas (SDD Section 20: shared/schemas/ — Pydantic models used by
both Phase 1 and Phase 2: TelemetryReading, TwinState, etc.)

Phase 1's FastAPI app defines these directly in
phase1_standalone/app/schemas.py to keep the single-process monolith
self-contained. This package re-exports the same models under the shared
namespace so Phase 2 services can `from shared.schemas import TwinState`
etc. without duplicating definitions or risking drift between phases.
"""
import os
import sys

_PHASE1_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "phase1_standalone")
if _PHASE1_ROOT not in sys.path:
    sys.path.insert(0, _PHASE1_ROOT)

from app.schemas import (  # noqa: E402,F401
    SourceEnum,
    ModeEnum,
    TelemetryReadingIn,
    TelemetryReadingOut,
    TwinState,
    RecommendationRequest,
    WaterModelOut,
    RecommendationOut,
    MemoryOut,
    DashboardSummary,
)
