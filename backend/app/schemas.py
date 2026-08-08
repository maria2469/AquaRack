"""
Pydantic schemas shared by the API routers, the Digital Twin Engine, and
the AI Decision Agent (SDD Section 10.2 — shared TelemetryReading schema;
Section 12.3 — TwinState output contract).
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SourceEnum(str, Enum):
    laptop = "laptop"
    opendc = "opendc"
    cloudsim = "cloudsim"
    iot = "iot"


class ModeEnum(str, Enum):
    laptop = "laptop"
    opendc = "opendc"
    cloudsim = "cloudsim"


# --- Telemetry (Section 10.2) ---

class TelemetryReadingIn(BaseModel):
    device_id: str
    rack_id: Optional[str] = None
    site_id: Optional[str] = None  # Phase 2: fleet/site tagging (FR-2.1, FR-2.9)
    timestamp: Optional[datetime] = None
    cpu_pct: float
    gpu_pct: Optional[float] = None
    ram_pct: float
    disk_io: Optional[float] = None
    fan_rpm: Optional[int] = None
    battery_pct: Optional[float] = None
    # Ambient weather, attached at collection time by run_collector.py via
    # app.services.weather_service. Optional so existing callers/tests that
    # don't set it still validate; downstream code treats None as "look it
    # up live" rather than silently defaulting to a hardcoded temperature.
    weather_temp: Optional[float] = None
    humidity: Optional[float] = None
    source: SourceEnum = SourceEnum.laptop


class TelemetryReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telemetry_id: str
    rack_id: Optional[str] = None
    site_id: Optional[str] = None
    device_id: str
    timestamp: datetime
    cpu_pct: float
    gpu_pct: Optional[float] = None
    ram_pct: float
    disk_io: Optional[float] = None
    fan_rpm: Optional[int] = None
    battery_pct: Optional[float] = None
    weather_temp: Optional[float] = None
    humidity: Optional[float] = None
    source: str


# --- Digital Twin (Section 12.3) ---

class TwinState(BaseModel):
    rack_id: str
    utilisation_pct: float
    thermal_load_kw: float
    power_draw_kw: float
    mode: ModeEnum = ModeEnum.laptop
    device_id: Optional[str] = "rack-01-primary"  # Add device_id for memory storage


# --- Simulate / Recommend requests ---

class RecommendationRequest(BaseModel):
    telemetry_id: Optional[str] = None


# --- Water Model (Section 13) ---

class WaterModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    water_model_id: str
    telemetry_id: str
    wue_factor: float
    cooling_load_kw: float
    water_l_per_hr: float
    pue: Optional[float] = None
    utilisation_pct: Optional[float] = None
    thermal_load_kw: Optional[float] = None
    power_draw_kw: Optional[float] = None
    computed_at: datetime


# --- Recommendation (Section 16.1 OUTPUT SCHEMA) ---

class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommendation_id: str
    telemetry_id: str
    memory_id: Optional[str] = None
    text: str
    confidence: float
    agent_name: str
    cited_memory_ids: List[str] = []
    rationale: Optional[str] = None
    created_at: datetime


# --- Memory (Section 11 / 15) ---

class MemoryOut(BaseModel):
    memory_id: str
    type: str
    summary_text: str
    tier: str
    created_at: datetime
    similarity: float


# --- Dashboard (Section 10.1 GET /dashboard/summary) ---

class DashboardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    latest_telemetry: Optional[TelemetryReadingOut] = None
    latest_water_model: Optional[WaterModelOut] = None
    latest_recommendation: Optional[RecommendationOut] = None
    telemetry_history: List[TelemetryReadingOut] = []
    open_incidents: int = 0