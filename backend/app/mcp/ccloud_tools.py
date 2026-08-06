"""
MCP Tools for CockroachDB Cloud (ccloud) CLI Integration.
Exposes cluster health and operational status checking tools for agents.
"""

import logging
from typing import Dict, Any, Optional
from app.cli.ccloud_wrapper import ccloud_cli

logger = logging.getLogger("aquamind.mcp_ccloud")


def ccloud_cluster_health(cluster_id: Optional[str] = None) -> Dict[str, Any]:
    """MCP Tool: Query CockroachDB Cloud cluster health & node status via ccloud CLI JSON API."""
    logger.info("MCP Tool Executed: ccloud_cluster_health(cluster_id='%s')", cluster_id)
    cid = cluster_id or "c1a2b3c4-rackpulse-cluster"
    res = ccloud_cli.run_command(["cluster", "inspect", cid])
    return {
        "tool": "ccloud_cluster_health",
        "cluster_id": cid,
        "health_data": res,
    }


def ccloud_list_clusters() -> Dict[str, Any]:
    """MCP Tool: List active CockroachDB Cloud clusters with JSON response."""
    logger.info("MCP Tool Executed: ccloud_list_clusters()")
    res = ccloud_cli.run_command(["cluster", "list"])
    return {
        "tool": "ccloud_list_clusters",
        "clusters_data": res,
    }
