"""
Memory / RAG Agent (SDD Phase 2, Section 6.1): "Retrieves and ranks
relevant historical incidents and recommendations."

Delegates to the shared tool layer's query_memory() (Section 6.2), so
retrieval logic is defined exactly once and reused by both Phase 1's
single agent and every Phase 2 peer agent that needs memory context.
"""
from typing import Dict

from sqlalchemy.orm import Session

from phase2_distributed.common import tool_layer


class MemoryRAGAgent:
    name = "memory_rag"

    def run(self, db: Session, query_text: str, k: int = 5) -> Dict:
        retrieved = tool_layer.query_memory(db, query_text, k=k)
        return {"agent": self.name, "query": query_text, "retrieved": retrieved}
