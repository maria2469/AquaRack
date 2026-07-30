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
    ram_pct = Column(Float, nullable=False)
    disk_io = Column(Float, nullable=True)
    fan_rpm = Column(Integer, nullable=True)
    battery_pct = Column(Float, nullable=True)
    source = Column(String, default="laptop")
    site_id = Column(String, nullable=True, index=True)  # Phase 2: fleet/site grouping (additive column)


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
    telemetry_id = Column(String, ForeignKey("telemetry.telemetry_id"), nullable=False)
    severity = Column(String, nullable=False)
    description = Column(String, nullable=False)
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
    """
    SDD Tech Stack: "CockroachDB Vector Index".

    `vector` is a plain SQLAlchemy JSON column so the ORM model works
    identically on SQLite and CockroachDB. On CockroachDB, a native
    `VECTOR(n)` column (`vector_native`) is ADDITIONALLY created on this
    table via raw DDL (see app.memory_engine.vector_index), kept in sync
    on every write, so similarity search can run as real SQL using
    CockroachDB's `<=>` cosine-distance operator directly in the
    database instead of pulling every row into Python. JSON remains the
    portable source of truth; `vector_native` is a CockroachDB-only
    derived index column.
    """
    __tablename__ = "embeddings"
    embedding_id = Column(String, primary_key=True, default=_uuid)
    memory_id = Column(String, ForeignKey("memories.memory_id"), nullable=False)
    vector = Column(JSON, nullable=False)  # list[float]; portable source of truth
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"
    recommendation_id = Column(String, primary_key=True, default=_uuid)
    telemetry_id = Column(String, ForeignKey("telemetry.telemetry_id"), nullable=False)
    memory_id = Column(String, ForeignKey("memories.memory_id"), nullable=True)
    text = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    agent_name = Column(String, nullable=False)  # 'rules_fallback' | 'bedrock_single'
    cited_memory_ids = Column(JSON, default=list)
    rationale = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
