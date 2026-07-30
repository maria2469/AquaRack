"""
Memory / RAG Agent (SDD Phase 2, Section 6.1): "Retrieves and ranks
relevant historical incidents and recommendations."

Delegates to the shared tool layer's query_memory() (Section 6.2), so
retrieval logic is defined exactly once and reused by both Phase 1's
single agent and every Phase 2 peer agent that needs memory context.
Retrieval is pushed to the real-time reasoning log as it happens.
"""
from typing import Dict

from sqlalchemy.orm import Session

from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.mcp.client import mcp_client
from app.observability import reasoning_logger as rl


class MemoryRAGAgent:
    name = "memory_rag"

    def run(self, db: Session, query_text: str, k: int = 5, run_id: Optional[str] = None) -> Dict:
        run_id = run_id or rl.new_run_id()
        rl.log_step(run_id, self.name, "tool_call", {"note": "Querying CockroachDB Managed MCP Server for historical memories", "query": query_text, "k": k})
        
        incidents = mcp_client.retrieve_similar_incidents(db, query_text=query_text, k=k)
        previous_recs = mcp_client.retrieve_previous_recommendations(db, query_text=query_text, k=k)
        
        combined_retrieved = []
        for inc in incidents:
            combined_retrieved.append({
                "memory_id": inc.get("incident_id"),
                "type": "incident",
                "summary_text": f"Incident {inc.get('severity', 'WARN')}: {inc.get('description')} (Cause: {inc.get('root_cause')})",
                "similarity": inc.get("similarity", 0.9),
                "created_at": inc.get("created_at"),
            })
        for rec in previous_recs:
            combined_retrieved.append({
                "memory_id": rec.get("recommendation_id"),
                "type": "recommendation",
                "summary_text": f"Previous Rec: {rec.get('recommendation_text')} (Saving: {rec.get('expected_water_saving')}%)",
                "similarity": rec.get("similarity", 0.9),
                "created_at": rec.get("created_at"),
            })
            
        rl.log_step(
            run_id, self.name, "decision",
            {"retrieved_count": len(combined_retrieved), "top_ids": [r["memory_id"] for r in combined_retrieved[:3]]},
        )
        return {"agent": self.name, "query": query_text, "retrieved": combined_retrieved, "incidents": incidents, "recommendations": previous_recs, "run_id": run_id}

