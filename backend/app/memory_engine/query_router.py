"""
NEW FILE -- the "biggest architectural improvement" from the diagnosis (issue #10),
wired up as an actual endpoint:

    User Query -> Cockroach VECTOR Search (incidents + recommendations, separately)
    -> Groq Llama 3.3 70B grounded synthesis -> JSON answer with sources

This is what your MCP demo endpoint should call instead of returning raw
retrieval results directly to the UI.
"""
import logging
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.mcp import tools as mcp_tools
from app.memory_engine.groq_synthesis import synthesize_grounded_answer

logger = logging.getLogger("aquamind.query_router")

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/grounded")
def grounded_query(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """
    Body: {"query_text": "...", "k": 5}

    Returns a grounded, cited answer built only from retrieved incident and
    recommendation memories -- see groq_synthesis.py for the no-hallucination
    contract enforced on the model.
    """
    query_text = payload.get("query_text", "")
    k = payload.get("k", 5)

    incident_result = mcp_tools.retrieve_similar_incidents(db, query_text=query_text, k=k)
    recommendation_result = mcp_tools.retrieve_previous_recommendations(db, query_text=query_text, k=k)

    logger.info(
        "grounded_query: incident_retrieval=%s recommendation_retrieval=%s",
        incident_result["retrieval_method"],
        recommendation_result["retrieval_method"],
    )

    synthesis = synthesize_grounded_answer(query_text, incident_result, recommendation_result)

    return {
        "query": query_text,
        "retrieval": {
            "incidents": {
                "retrieval_method": incident_result["retrieval_method"],
                "embedding_model": incident_result.get("embedding_model"),
                "searched_records": incident_result.get("searched_records"),
                "matches": incident_result["matches"],
            },
            "recommendations": {
                "retrieval_method": recommendation_result["retrieval_method"],
                "embedding_model": recommendation_result.get("embedding_model"),
                "searched_records": recommendation_result.get("searched_records"),
                "matches": recommendation_result["matches"],
            },
        },
        "synthesis": synthesis,
    }