"""
CockroachDB Managed MCP Tools implementation for RackPulse.

Provides structured MCP memory retrieval and persistence tools used by Ollama/Groq via llm_client and Agent Orchestrators.

FIXES APPLIED (see diagnosis doc):
  - Removed hardcoded fallback similarity (0.85 / 0.88). Fallback results now carry
    retrieval_method="fallback" and similarity=None so callers/UI can distinguish
    "real vector match" from "we just grabbed the most recent rows".
  - Every result now reports retrieval_method so you can verify in logs/UI whether
    Cockroach VECTOR search actually fired.
  - retrieve_similar_incidents / retrieve_previous_recommendations no longer get
    silently mixed together by callers -- each stays scoped to its own memory_type.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app import models
from app.memory_engine import store as memory_store

logger = logging.getLogger("aquamind.mcp_tools")


def retrieve_similar_incidents(db: Session, query_text: str, k: int = 5) -> Dict[str, Any]:
    """MCP Tool: Retrieve top-K similar incidents via CockroachDB vector index search.

    Returns a dict (not a bare list) so retrieval_method / embedding_model / counts
    are visible to the caller and to logs -- this is what tells you whether you're
    actually hitting Cockroach VECTOR search or the fallback path.
    """
    logger.info("MCP Tool Executed: retrieve_similar_incidents(query='%s', k=%d)", query_text, k)

    search_result = memory_store.search_memory_embeddings(
        db, query_text, memory_type="incident", k=k
    )
    embeddings = search_result["matches"]
    retrieval_method = search_result["retrieval_method"]

    results = []
    for emb in embeddings:
        inc = db.get(models.Incident, emb["source_id"])
        results.append({
            "incident_id": emb["source_id"],
            "summary": emb["summary"],
            "similarity": emb["similarity"],
            "severity": inc.severity if inc else "UNKNOWN",
            "description": inc.description if inc else emb["summary"],
            "root_cause": inc.root_cause if inc else None,
            "created_at": str(emb["created_at"]),
        })

    if not results:
        logger.warning(
            "No vector matches for incident query '%s' -- falling back to most-recent-N. "
            "This is NOT a semantic match.", query_text
        )
        retrieval_method = "fallback_recent"
        incidents = (
            db.query(models.Incident)
            .order_by(models.Incident.created_at.desc())
            .limit(k)
            .all()
        )
        results = [
            {
                "incident_id": inc.incident_id,
                "summary": inc.description,
                "similarity": None,  # honest: we did not compute a similarity score
                "severity": inc.severity,
                "description": inc.description,
                "root_cause": inc.root_cause,
                "created_at": str(inc.created_at),
            }
            for inc in incidents
        ]

    return {
        "query": query_text,
        "matches": results,
        "retrieval_method": retrieval_method,
        "embedding_model": search_result.get("embedding_model"),
        "searched_records": search_result.get("searched_records", 0),
    }


def retrieve_previous_recommendations(db: Session, query_text: str, k: int = 5) -> Dict[str, Any]:
    """MCP Tool: Retrieve top-K previous recommendations via CockroachDB vector index search."""
    logger.info("MCP Tool Executed: retrieve_previous_recommendations(query='%s', k=%d)", query_text, k)

    search_result = memory_store.search_memory_embeddings(
        db, query_text, memory_type="recommendation", k=k
    )
    embeddings = search_result["matches"]
    retrieval_method = search_result["retrieval_method"]

    results = []
    for emb in embeddings:
        rec = db.get(models.Recommendation, emb["source_id"])
        results.append({
            "recommendation_id": emb["source_id"],
            "summary": emb["summary"],
            "similarity": emb["similarity"],
            "recommendation_text": rec.text if rec else emb["summary"],
            "expected_water_saving": rec.expected_water_saving if rec else None,
            "confidence": rec.confidence if rec else None,
            "created_at": str(emb["created_at"]),
        })

    if not results:
        logger.warning(
            "No vector matches for recommendation query '%s' -- falling back to most-recent-N.",
            query_text
        )
        retrieval_method = "fallback_recent"
        recs = (
            db.query(models.Recommendation)
            .order_by(models.Recommendation.created_at.desc())
            .limit(k)
            .all()
        )
        results = [
            {
                "recommendation_id": r.recommendation_id,
                "summary": r.text,
                "similarity": None,
                "recommendation_text": r.text,
                "expected_water_saving": r.expected_water_saving,
                "confidence": r.confidence,
                "created_at": str(r.created_at),
            }
            for r in recs
        ]

    return {
        "query": query_text,
        "matches": results,
        "retrieval_method": retrieval_method,
        "embedding_model": search_result.get("embedding_model"),
        "searched_records": search_result.get("searched_records", 0),
    }


def retrieve_water_saving_history(db: Session, rack_id: Optional[str] = None, k: int = 10) -> List[Dict[str, Any]]:
    """MCP Tool: Retrieve historical water savings metrics from CockroachDB."""
    logger.info("MCP Tool Executed: retrieve_water_saving_history(rack_id='%s', k=%d)", rack_id, k)
    query = db.query(models.WaterModelResult).order_by(models.WaterModelResult.computed_at.desc())
    if rack_id:
        # NOTE: assumes WaterModelResult has a rack_id column. If it doesn't in your
        # schema, this filter needs to join through Telemetry instead -- flag this
        # to me if rack_id filtering silently does nothing.
        query = query.filter(models.WaterModelResult.rack_id == rack_id)
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
            "gpu_temp": r.gpu_temp,
            "ram_pct": r.ram_pct,
            "timestamp": str(r.timestamp),
        }
        for r in rows
    ]


def store_agent_memory(db: Session, memory_type: str, source_id: str, summary: str) -> Dict[str, Any]:
    """MCP Tool: Persist a new memory entry + embedding into CockroachDB.

    Callers should pass a RICH summary (specific numbers, root cause, action taken,
    outcome) rather than a templated one-liner -- see build_incident_summary() /
    build_recommendation_summary() in memory_engine/summarize.py. Near-identical
    summaries produce near-identical embeddings, which is why every query used to
    match everything.
    """
    logger.info("MCP Tool Executed: store_agent_memory(type='%s', source_id='%s')", memory_type, source_id)
    emb = memory_store.store_memory_embedding(db, memory_type=memory_type, source_id=source_id, summary=summary)
    return {
        "status": "success",
        "id": emb.id,
        "memory_type": emb.memory_type,
        "source_id": emb.source_id,
        "summary": emb.summary,
    }


def hybrid_search_incidents(
    db: Session,
    query_text: str,
    rack_id: Optional[str] = None,
    min_severity: Optional[str] = None,
    time_range_hours: Optional[int] = None,
    k: int = 5,
) -> Dict[str, Any]:
    """MCP Tool: Native Hybrid Vector + Structured Search in CockroachDB."""
    logger.info("MCP Tool Executed: hybrid_search_incidents(query='%s', rack_id='%s')", query_text, rack_id)
    res = memory_store.search_memory_embeddings_hybrid(
        db=db,
        query_text=query_text,
        memory_type="incident",
        rack_id=rack_id,
        min_severity=min_severity,
        time_range_hours=time_range_hours,
        k=k,
    )
    return res


def retrieve_similar_episodes(
    db: Session,
    query_text: str,
    rack_id: Optional[str] = None,
    k: int = 5,
) -> List[Dict[str, Any]]:
    """
    MCP Tool: Retrieve top-K historically similar Episodes by cosine similarity on
    Episode.embedding (Task 7 — Episode-First Retrieval).

    Falls back to most-recent resolved episodes if embeddings are absent.
    Returns list of dicts with episode context usable as priors for the optimizer.
    """
    logger.info(
        "MCP Tool Executed: retrieve_similar_episodes(query='%s', rack_id='%s', k=%d)",
        query_text, rack_id, k,
    )
    from app.models_ext import Episode
    from app.memory_engine.embed import embed_text
    import json

    try:
        query_vec, _ = embed_text(query_text)
    except Exception as e:
        logger.warning("embed_text failed in retrieve_similar_episodes: %s", e)
        query_vec = None

    results: List[Dict[str, Any]] = []

    if query_vec:
        # Attempt vector similarity scan over resolved episodes
        resolved = (
            db.query(Episode)
            .filter(Episode.outcome_recorded_at.isnot(None))
            .filter(Episode.embedding.isnot(None))
        )
        if rack_id:
            resolved = resolved.filter(Episode.rack_id == rack_id)
        candidates = resolved.order_by(Episode.created_at.desc()).limit(200).all()

        scored = []
        for ep in candidates:
            emb = ep.embedding
            if not emb or not isinstance(emb, list):
                continue
            try:
                # Cosine similarity (vectors are unit-normalised by embed_text)
                dot = sum(a * b for a, b in zip(query_vec, emb))
                scored.append((dot, ep))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        for sim, ep in scored[:k]:
            results.append({
                "episode_id": ep.episode_id,
                "action_taken": ep.action_taken,
                "confidence_at_decision": ep.confidence_at_decision,
                "water_delta_pct": ep.water_delta_pct,
                "temp_delta_c": ep.temp_delta_c,
                "success": ep.success,
                "reward": ep.reward,
                "similarity": round(sim, 4),
                "retrieval_method": "vector",
            })

    if not results:
        # Fallback: most-recent resolved episodes
        logger.warning("No episode vector matches — using most-recent fallback.")
        from app.models_ext import Episode as _Ep
        q = db.query(_Ep).filter(_Ep.outcome_recorded_at.isnot(None))
        if rack_id:
            q = q.filter(_Ep.rack_id == rack_id)
        for ep in q.order_by(_Ep.created_at.desc()).limit(k).all():
            results.append({
                "episode_id": ep.episode_id,
                "action_taken": ep.action_taken,
                "confidence_at_decision": ep.confidence_at_decision,
                "water_delta_pct": ep.water_delta_pct,
                "temp_delta_c": ep.temp_delta_c,
                "success": ep.success,
                "reward": ep.reward,
                "similarity": None,
                "retrieval_method": "fallback_recent",
            })

    return results