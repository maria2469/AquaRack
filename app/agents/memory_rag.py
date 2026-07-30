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

from app import tool_layer
from app.observability import reasoning_logger as rl


class MemoryRAGAgent:
    name = "memory_rag"

    def run(self, db: Session, query_text: str, k: int = 5, run_id: str = None) -> Dict:
        run_id = run_id or rl.new_run_id()
        rl.log_step(run_id, self.name, "tool_call", {"note": "Querying vector memory (RAG)", "query": query_text, "k": k})
        retrieved = tool_layer.query_memory(db, query_text, k=k)
        rl.log_step(
            run_id, self.name, "decision",
            {"retrieved_count": len(retrieved), "top_ids": [r["memory_id"] for r in retrieved[:3]]},
        )
        return {"agent": self.name, "query": query_text, "retrieved": retrieved, "run_id": run_id}
