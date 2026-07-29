"""
Phase 2 schema extension (SDD Phase 2, Section 10.1: "Phase 2 adds table
locality settings ... no columns are removed or renamed"). These are NEW
tables only — nothing in phase1_standalone/app/models.py is replaced.

- Site               : fleet/site registry (FR-2.6 fleet-wide dashboards;
                        FR-2.4 REGIONAL/GLOBAL table locality per site/region)
- SimulationJob       : async OpenDC/CloudSim job tracking (FR-2.2)
- Feedback            : human feedback on recommendations (Section 11.1
                         endpoint POST /api/v1/agents/feedback)
- CDCExportLog        : record of memories exported to the simulated S3
                        cold-tier data lake (FR-2.5 / Section 12.2)
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON

import phase2_distributed.common.pathsetup  # noqa: F401  (wire sys.path first)
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Site(Base):
    __tablename__ = "sites"
    site_id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    region = Column(String, nullable=True)  # e.g. us-east-1 (CockroachDB table locality, Section 5.2/19)
    table_locality = Column(String, default="REGIONAL")  # REGIONAL | GLOBAL (FR-2.4)
    created_at = Column(DateTime, default=datetime.utcnow)


class SimulationJob(Base):
    __tablename__ = "simulation_jobs"
    job_id = Column(String, primary_key=True, default=_uuid)
    mode = Column(String, nullable=False)  # opendc | cloudsim (FR-2.2)
    spec = Column(JSON, default=dict)
    status = Column(String, default="queued")  # queued | running | completed | failed
    progress_pct = Column(Float, default=0.0)
    result = Column(JSON, nullable=True)  # checkpointed partial/final results (Section 15.3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "recommendation_feedback"
    feedback_id = Column(String, primary_key=True, default=_uuid)
    recommendation_id = Column(String, ForeignKey("recommendations.recommendation_id"), nullable=False)
    rating = Column(Integer, nullable=False)  # e.g. -1 / 0 / 1, or a 1-5 scale
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CDCExportLog(Base):
    __tablename__ = "cdc_export_log"
    export_id = Column(String, primary_key=True, default=_uuid)
    memory_id = Column(String, ForeignKey("memories.memory_id"), nullable=False)
    exported_at = Column(DateTime, default=datetime.utcnow)
    s3_uri = Column(String, nullable=False)  # simulated local path standing in for a real S3 URI
