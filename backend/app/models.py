"""
SQLAlchemy ORM models — implements the ER diagram in SDD Section 9 exactly
(table names, key columns) so nothing needs renaming when Phase 2 points
the same schema at a multi-node CockroachDB cluster.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, ForeignKeyConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Rack(Base):
    __tablename__ = "racks"
    rack_id = Column(String, primary_key=True, default=_uuid)
    capacity_kw = Column(Float, nullable=False)
    node_count = Column(Integer, nullable=False, default=1)
    location = Column(String, nullable=True)
    site_id = Column(String, nullable=True, index=True)  # Phase 2: fleet/site grouping (additive column)
    created_at = Column(DateTime, default=datetime.utcnow)


class RackConfig(Base):
    __tablename__ = "racks_config"
    config_id = Column(String, primary_key=True, default=_uuid)
    rack_id = Column(String, ForeignKey("racks.rack_id"), nullable=False)
    mode = Column(String, default="laptop")  # laptop | opendc | cloudsim
    sim_params = Column(JSON, default=dict)


class Telemetry(Base):
    __tablename__ = "telemetry"
    telemetry_id = Column(String, primary_key=True, default=_uuid)
    rack_id = Column(String, ForeignKey("racks.rack_id"), nullable=True)
    device_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    cpu_pct = Column(Float, nullable=False)
    gpu_pct = Column(Float, nullable=True)
    gpu_temp = Column(Float, nullable=True)
    ram_pct = Column(Float, nullable=False)
    disk_io = Column(Float, nullable=True)
    fan_rpm = Column(Integer, nullable=True)
    battery_pct = Column(Float, nullable=True)
    weather_temp = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    predicted_water_usage = Column(Float, nullable=True)
    source = Column(String, default="laptop")
    site_id = Column(String, nullable=True, index=True)  # Phase 2: fleet/site grouping (additive column)

    @property
    def cpu_usage(self) -> float:
        return self.cpu_pct

    @property
    def gpu_usage(self) -> float:
        return self.gpu_pct or 0.0

    @property
    def ram_usage(self) -> float:
        return self.ram_pct


class Weather(Base):
    __tablename__ = "weather"
    weather_id = Column(String, primary_key=True, default=_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ambient_temp = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    location = Column(String, nullable=True)
    source = Column(String, default="cached")


class WaterModelResult(Base):
    __tablename__ = "water_model"
    water_model_id = Column(String, primary_key=True, default=_uuid)
    telemetry_id = Column(String, ForeignKey("telemetry.telemetry_id"), nullable=False)
    wue_factor = Column(Float, nullable=False)
    cooling_load_kw = Column(Float, nullable=False)
    water_l_per_hr = Column(Float, nullable=False)
    pue = Column(Float, nullable=True)
    utilisation_pct = Column(Float, nullable=True)
    thermal_load_kw = Column(Float, nullable=True)
    power_draw_kw = Column(Float, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)


class Incident(Base):
    __tablename__ = "incidents"
    incident_id = Column(String, primary_key=True, default=_uuid)
    telemetry_id = Column(String, ForeignKey("telemetry.telemetry_id"), nullable=True)
    severity = Column(String, nullable=False)
    description = Column(String, nullable=False)
    root_cause = Column(String, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Maintenance(Base):
    __tablename__ = "maintenance"
    maintenance_id = Column(String, primary_key=True, default=_uuid)
    rack_id = Column(String, ForeignKey("racks.rack_id"), nullable=True)
    type = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    performed_at = Column(DateTime, default=datetime.utcnow)
    performed_by = Column(String, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    audit_id = Column(String, primary_key=True, default=_uuid)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity_ref = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    conversation_id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    channel = Column(String, nullable=True)


class Memory(Base):
    __tablename__ = "memories"
    memory_id = Column(String, primary_key=True, default=_uuid)
    conversation_id = Column(String, ForeignKey("conversations.conversation_id"), nullable=True)
    type = Column(String, nullable=False)
    summary_text = Column(String, nullable=False)
    tier = Column(String, default="hot")  # hot|warm|cold (tiering is a Phase 2 concern)
    created_at = Column(DateTime, default=datetime.utcnow)


class Embedding(Base):
    __tablename__ = "embeddings"
    embedding_id = Column(String, primary_key=True, default=_uuid)
    memory_id = Column(String, ForeignKey("memories.memory_id"), nullable=False)
    vector = Column(JSON, nullable=False)  # list[float]; portable source of truth
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MemoryEmbedding(Base):
    """
    Enterprise Agentic Memory Embedding Table.
    Stores semantic vector representation for any incident, recommendation, or operational summary.
    """
    __tablename__ = "memory_embeddings"
    id = Column(String, primary_key=True, default=_uuid)
    device_id = Column(String, nullable=False, index=True)  # Device-specific memory isolation
    memory_type = Column(String, nullable=False, index=True)  # incident | recommendation | summary | telemetry
    source_id = Column(String, nullable=False, index=True)
    embedding = Column(JSON, nullable=False)
    summary = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"
    recommendation_id = Column(String, primary_key=True, default=_uuid)
    device_id = Column(String, nullable=False, index=True)  # Device-specific recommendations
    telemetry_id = Column(String, ForeignKey("telemetry.telemetry_id"), nullable=True)
    incident_id = Column(String, ForeignKey("incidents.incident_id"), nullable=True)
    memory_id = Column(String, ForeignKey("memories.memory_id"), nullable=True)
    text = Column(String, nullable=False)
    expected_water_saving = Column(Float, nullable=True, default=0.0)
    confidence = Column(Float, nullable=False)
    agent_name = Column(String, nullable=False)  # 'langgraph_multi_agent' | 'multi_agent_orchestrator'
    cited_memory_ids = Column(JSON, default=list)
    rationale = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

