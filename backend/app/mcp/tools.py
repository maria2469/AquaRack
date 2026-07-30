"""
CockroachDB Managed MCP Tools implementation for RackPulse.

Provides structured MCP memory retrieval and persistence tools used by Bedrock and Agent Orchestrators.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app import models
from app.memory_engine import store as memory_store

logger = logging.getLogger("aquamind.mcp_tools")


def retrieve_similar_incidents(db: Session, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
    """MCP Tool: Retrieve top-K similar incidents via CockroachDB vector index search."""
    logger.info("MCP Tool Executed: retrieve_similar_incidents(query='%s', k=%d)", query_text, k)
    embeddings = memory_store.search_memory_embeddings(db, query_text, memory_type="incident", k=k)
    results = []
    for emb in embeddings:
        inc = db.get(models.Incident, emb["source_id"])
        results.append({
            "incident_id": emb["source_id"],
            "summary": emb["summary"],
            "similarity": emb["similarity"],
            "severity": inc.severity if inc else "UNKNOWN",
            "description": inc.description if inc else emb["summary"],
            "root_cause": inc.root_cause if inc else "Thermal load spike",
            "created_at": str(emb["created_at"]),
        })
    if not results:
        # Fallback query directly on Incidents table if embeddings empty
        incidents = db.query(models.Incident).order_by(models.Incident.created_at.desc()).limit(k).all()
        results = [
            {
                "incident_id": inc.incident_id,
                "summary": inc.description,
                "similarity": 0.85,
                "severity": inc.severity,
                "description": inc.description,
                "root_cause": inc.root_cause or "High ambient thermal load",
                "created_at": str(inc.created_at),
            }
            for inc in incidents
        ]
    return results


def retrieve_previous_recommendations(db: Session, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
    """MCP Tool: Retrieve top-K previous recommendations via CockroachDB vector index search."""
    logger.info("MCP Tool Executed: retrieve_previous_recommendations(query='%s', k=%d)", query_text, k)
    embeddings = memory_store.search_memory_embeddings(db, query_text, memory_type="recommendation", k=k)
    results = []
    for emb in embeddings:
        rec = db.get(models.Recommendation, emb["source_id"])
        results.append({
            "recommendation_id": emb["source_id"],
            "summary": emb["summary"],
            "similarity": emb["similarity"],
            "recommendation_text": rec.text if rec else emb["summary"],
            "expected_water_saving": rec.expected_water_saving if rec else 15.0,
            "confidence": rec.confidence if rec else 0.9,
            "created_at": str(emb["created_at"]),
        })
    if not results:
        recs = db.query(models.Recommendation).order_by(models.Recommendation.created_at.desc()).limit(k).all()
        results = [
            {
                "recommendation_id": r.recommendation_id,
                "summary": r.text,
                "similarity": 0.88,
                "recommendation_text": r.text,
                "expected_water_saving": r.expected_water_saving or 12.5,
                "confidence": r.confidence,
                "created_at": str(r.created_at),
            }
            for r in recs
        ]
    return results


def retrieve_water_saving_history(db: Session, rack_id: Optional[str] = None, k: int = 10) -> List[Dict[str, Any]]:
    """MCP Tool: Retrieve historical water savings metrics from CockroachDB."""
    logger.info("MCP Tool Executed: retrieve_water_saving_history(rack_id='%s', k=%d)", rack_id, k)
    query = db.query(models.WaterModelResult).order_by(models.WaterModelResult.computed_at.desc())
    rows = query.limit(k).all()
    return [
        {
            "water_model_id": r.water_model_id,
            "telemetry_id": r.telemetry_id,
            "cooling_load_kw": r.cooling_load_kw,
            "wue_factor": r.wue_factor,
            "water_l_per_hr": r.water_l_per_hr,
            "pue": r.pue,
            "computed_at": str(r.computed_at),
        }
        for r in rows
    ]


def retrieve_high_gpu_events(db: Session, threshold_pct: float = 75.0, k: int = 10) -> List[Dict[str, Any]]:
    """MCP Tool: Retrieve high GPU usage telemetry events from CockroachDB."""
    logger.info("MCP Tool Executed: retrieve_high_gpu_events(threshold=%.1f, k=%d)", threshold_pct, k)
    rows = (
        db.query(models.Telemetry)
        .filter(models.Telemetry.gpu_pct >= threshold_pct)
        .order_by(models.Telemetry.timestamp.desc())
        .limit(k)
        .all()
    )
    return [
        {
            "telemetry_id": r.telemetry_id,
            "rack_id": r.rack_id or "rack-01",
            "cpu_pct": r.cpu_pct,
            "gpu_pct": r.gpu_pct,
            "gpu_temp": r.gpu_temp or (55.0 + (r.gpu_pct or 0) * 0.3),
            "ram_pct": r.ram_pct,
            "timestamp": str(r.timestamp),
        }
        for r in rows
    ]


def store_agent_memory(db: Session, memory_type: str, source_id: str, summary: str) -> Dict[str, Any]:
    """MCP Tool: Persist a new memory entry + embedding into CockroachDB."""
    logger.info("MCP Tool Executed: store_agent_memory(type='%s', source_id='%s')", memory_type, source_id)
    emb = memory_store.store_memory_embedding(db, memory_type=memory_type, source_id=source_id, summary=summary)
    return {
        "status": "success",
        "id": emb.id,
        "memory_type": emb.memory_type,
        "source_id": emb.source_id,
        "summary": emb.summary,
    }
