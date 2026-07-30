"""
Reusable CockroachDB Managed MCP Client.

Routes AI Agent memory requests to either the remote CockroachDB Cloud Managed MCP Server
endpoint via HTTP/JSON-RPC or to local MCP Tool executions when running standalone.
"""
import logging
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session

from app.mcp.config import mcp_config
from app.mcp import tools as mcp_tools

logger = logging.getLogger("aquamind.mcp_client")


class CockroachMCPClient:
    """Reusable CockroachDB Managed MCP Server Client."""

    def __init__(self):
        self.endpoint = mcp_config.COCKROACH_MCP_ENDPOINT
        self.api_key = mcp_config.COCKROACH_MCP_API_KEY
        self.enabled = mcp_config.MCP_ENABLED

    def _call_remote_mcp(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """Calls remote CockroachDB Managed MCP Server via JSON-RPC over HTTP."""
        if not self.endpoint:
            return None
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            with httpx.Client(timeout=mcp_config.MCP_TIMEOUT_SECONDS) as client:
                resp = client.post(self.endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if "result" in data:
                    return data["result"]
        except Exception as exc:
            logger.warning("Remote MCP Server call failed (%s), using local MCP tools: %s", tool_name, exc)
        return None

    def retrieve_similar_incidents(self, db: Session, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve similar incidents via MCP Server."""
        remote = self._call_remote_mcp("retrieve_similar_incidents", {"query_text": query_text, "k": k})
        if remote is not None:
            return remote
        return mcp_tools.retrieve_similar_incidents(db, query_text=query_text, k=k)

    def retrieve_previous_recommendations(self, db: Session, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve previous recommendations via MCP Server."""
        remote = self._call_remote_mcp("retrieve_previous_recommendations", {"query_text": query_text, "k": k})
        if remote is not None:
            return remote
        return mcp_tools.retrieve_previous_recommendations(db, query_text=query_text, k=k)

    def retrieve_water_saving_history(self, db: Session, rack_id: Optional[str] = None, k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve water saving history via MCP Server."""
        remote = self._call_remote_mcp("retrieve_water_saving_history", {"rack_id": rack_id, "k": k})
        if remote is not None:
            return remote
        return mcp_tools.retrieve_water_saving_history(db, rack_id=rack_id, k=k)

    def retrieve_high_gpu_events(self, db: Session, threshold_pct: float = 75.0, k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve high GPU events via MCP Server."""
        remote = self._call_remote_mcp("retrieve_high_gpu_events", {"threshold_pct": threshold_pct, "k": k})
        if remote is not None:
            return remote
        return mcp_tools.retrieve_high_gpu_events(db, threshold_pct=threshold_pct, k=k)

    def store_agent_memory(self, db: Session, memory_type: str, source_id: str, summary: str) -> Dict[str, Any]:
        """Store agent memory via MCP Server."""
        remote = self._call_remote_mcp(
            "store_agent_memory",
            {"memory_type": memory_type, "source_id": source_id, "summary": summary},
        )
        if remote is not None:
            return remote
        return mcp_tools.store_agent_memory(db, memory_type=memory_type, source_id=source_id, summary=summary)


mcp_client = CockroachMCPClient()
