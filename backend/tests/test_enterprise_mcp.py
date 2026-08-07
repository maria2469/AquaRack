import os
os.environ["DATABASE_URL"] = "sqlite:///./test_aquamind_mcp.db"
os.environ["OLLAMA_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_enterprise_telemetry_and_dashboard():
    response = client.get("/api/telemetry/latest")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_usage" in data
    assert "gpu_usage" in data
    assert "weather_temp" in data

    dash_resp = client.get("/api/dashboard")
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert "current_gpu" in dash_data
    assert "memory_confidence_pct" in dash_data
    assert "opendc_fleet" in dash_data


def test_mcp_tools_and_reasoning_loop():
    # Test MCP tool discovery endpoint
    tools_resp = client.get("/mcp/tools")
    assert tools_resp.status_code == 200
    tools = tools_resp.json()["tools"]
    tool_names = [t["name"] for t in tools]
    assert "retrieve_similar_incidents" in tool_names
    assert "retrieve_previous_recommendations" in tool_names

    # Test MCP JSON-RPC execution
    rpc_resp = client.post(
        "/mcp/rpc",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "retrieve_similar_incidents",
                "arguments": {"query_text": "thermal load GPU 90%", "k": 3},
            },
        },
    )
    assert rpc_resp.status_code == 200
    rpc_res = rpc_resp.json()
    assert "result" in rpc_res

    # Test POST /api/reason
    reason_resp = client.post("/api/reason", json={})
    assert reason_resp.status_code == 200
    reason_data = reason_resp.json()
    assert "recommendation" in reason_data
    assert "confidence_pct" in reason_data
    assert "expected_water_saving" in reason_data

    # Test POST /api/reason with use_memory=false (baseline mode)
    baseline_resp = client.post("/api/reason", json={"use_memory": False})
    assert baseline_resp.status_code == 200
    baseline_data = baseline_resp.json()
    assert baseline_data.get("use_memory") is False
    assert baseline_data.get("cited_episodes_count") == 0

    # Test POST /api/compare — side-by-side benchmark
    compare_resp = client.post("/api/compare", json={})
    assert compare_resp.status_code == 200
    compare_data = compare_resp.json()
    assert "scenario" in compare_data
    assert "without_memory" in compare_data
    assert "with_memory" in compare_data
    assert compare_data["without_memory"]["use_memory"] is False
    assert compare_data["with_memory"]["use_memory"] is True
    assert compare_data["scenario"]["utilisation"] is not None


def test_memory_search_endpoint():
    search_resp = client.post("/api/memory/search", json={"query": "high GPU water savings", "k": 5})
    assert search_resp.status_code == 200
    res = search_resp.json()
    assert "similar_incidents" in res
    assert "previous_recommendations" in res
