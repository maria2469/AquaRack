"""
CockroachDB Agent Skills MCP Integration module.
Provides schema guidelines and CockroachDB query tuning guidance to agents.
"""

from typing import Dict, Any


def get_cockroachdb_skills_guidance() -> Dict[str, Any]:
    """Returns official CockroachDB Agent Skills best practices for schema, vector index, and hybrid queries."""
    return {
        "skill": "cockroachdb-agent-skills",
        "guidelines": {
            "vector_dimension": 1024,
            "vector_index_syntax": "CREATE VECTOR INDEX IF NOT EXISTS memory_embeddings_vector_idx ON memory_embeddings(vector_native);",
            "distance_operator": "<=> (Cosine distance)",
            "hybrid_search_pattern": "Combine vector_native <=> CAST(:vec AS VECTOR) with structured WHERE predicates (memory_type, rack_id, created_at)",
            "ccloud_health_check": "Execute ccloud_cluster_health before major schema mutations",
        },
    }
