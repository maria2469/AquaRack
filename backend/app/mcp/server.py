"""
CockroachDB Managed MCP Server FastAPI endpoint wrapper.
Exposes JSON-RPC 2.0 / MCP tool discovery and tool execution handlers.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.mcp import tools as mcp_tools

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/tools")
def list_mcp_tools():
    """Returns definitions of all registered CockroachDB Managed MCP tools."""
    return {
        "tools": [
            {
                "name": "retrieve_similar_incidents",
                "description": "Retrieve top-K similar incidents via CockroachDB vector index",
                "parameters": {"query_text": "string", "k": "integer"},
            },
            {
                "name": "retrieve_previous_recommendations",
                "description": "Retrieve top-K previous recommendations via CockroachDB vector index",
                "parameters": {"query_text": "string", "k": "integer"},
            },
            {
                "name": "retrieve_water_saving_history",
                "description": "Retrieve historical water saving metrics from CockroachDB",
                "parameters": {"rack_id": "string", "k": "integer"},
            },
            {
                "name": "retrieve_high_gpu_events",
                "description": "Retrieve high GPU usage telemetry events from CockroachDB",
                "parameters": {"threshold_pct": "number", "k": "integer"},
            },
            {
                "name": "store_agent_memory",
                "description": "Store a new agent memory and embedding into CockroachDB",
                "parameters": {"memory_type": "string", "source_id": "string", "summary": "string"},
            },
        ]
    }


@router.post("/rpc")
def handle_mcp_rpc(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """JSON-RPC 2.0 endpoint for CockroachDB Managed MCP Server tool execution."""
    method = payload.get("method")
    params = payload.get("params", {})
    req_id = payload.get("id", 1)

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": list_mcp_tools()}

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "retrieve_similar_incidents":
            res = mcp_tools.retrieve_similar_incidents(db, query_text=args.get("query_text", ""), k=args.get("k", 5))
        elif name == "retrieve_previous_recommendations":
            res = mcp_tools.retrieve_previous_recommendations(db, query_text=args.get("query_text", ""), k=args.get("k", 5))
        elif name == "retrieve_water_saving_history":
            res = mcp_tools.retrieve_water_saving_history(db, rack_id=args.get("rack_id"), k=args.get("k", 10))
        elif name == "retrieve_high_gpu_events":
            res = mcp_tools.retrieve_high_gpu_events(db, threshold_pct=args.get("threshold_pct", 75.0), k=args.get("k", 10))
        elif name == "store_agent_memory":
            res = mcp_tools.store_agent_memory(
                db,
                memory_type=args.get("memory_type", "summary"),
                source_id=args.get("source_id", ""),
                summary=args.get("summary", ""),
                device_id=args.get("device_id", "rack-01-primary"),
            )
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Tool '{name}' not found"}}

        return {"jsonrpc": "2.0", "id": req_id, "result": res}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method '{method}' not recognized"}}
