"""
Pydantic schemas for Phase 2's additional endpoints (SDD Phase 2, Section
11.1). These sit alongside — and reuse where possible — the shared
TelemetryReading / TwinState / WaterModelOut / RecommendationOut schemas
already defined in phase1_standalone/app/schemas.py.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- POST /api/v1/simulate/opendc (FR-2.2) ---

class SimulationJobSpec(BaseModel):
    mode: str = Field("opendc", pattern="^(opendc|cloudsim)$")
    num_racks: int = Field(5, ge=1, le=200)
    workload_profile: str = Field(
        "steady", pattern="^(steady|bursty|cpu_intensive|idle)$"
    )
    duration_ticks: int = Field(20, ge=1, le=500)
    capacity_kw: float = 8.0
    node_count: int = 4
    site_name: Optional[str] = None
    region: Optional[str] = "sim-region-1"


class SimulationJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    mode: str
    status: str
    progress_pct: float
    created_at: datetime
    updated_at: datetime


class SimulationJobResult(SimulationJobOut):
    result: Optional[Dict[str, Any]] = None


# --- GET /api/v1/sites (fleet view) ---

class SiteOut(BaseModel):
    rack_id: str
    site_id: Optional[str] = None
    name: Optional[str] = None
    region: Optional[str] = None
    capacity_kw: float
    node_count: int
    location: Optional[str] = None
    mode: Optional[str] = None


# --- POST /api/v1/agents/feedback ---

class FeedbackIn(BaseModel):
    recommendation_id: str
    rating: int = Field(..., ge=-1, le=5)
    notes: Optional[str] = None


# --- Multi-agent /api/v1/recommend response (adds agent_trace on top of
#     the Phase 1 RecommendationOut shape — additive, not breaking) ---

class MultiAgentRecommendationOut(BaseModel):
    recommendation_id: str
    telemetry_id: str
    memory_id: Optional[str] = None
    text: str
    confidence: float
    agent_name: str
    cited_memory_ids: List[str] = []
    rationale: Optional[str] = None
    created_at: datetime
    agent_trace: List[Dict[str, Any]] = []
    run_id: Optional[str] = None
