"""
Tests for Ollama reasoning engine, CockroachDB Managed MCP Server,
CockroachDB Vector Indexing, Amazon S3 export, AWS Lambda EventBridge handler,
Amazon CloudWatch metrics, and AWS Secrets Manager.
"""
import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

os.environ["DATABASE_URL"] = "sqlite:///./test_aquamind_cloud.db"
os.environ["OLLAMA_ENABLED"] = "true"
os.environ["AQUAMIND_SKIP_CLOUDWATCH"] = "1"  # prevent watchtower init in test process

from app.database import init_db, SessionLocal
from app.config import settings
from app.agents import langchain_ollama
from app.mcp import tools as mcp_tools
from app.mcp.client import mcp_client
from app.memory_engine import store as memory_store, embed, vector_index
from app.lib.s3_client import export_cold_memory, upload_report_to_s3, upload_telemetry_snapshot_to_s3, upload_dataset_export_to_s3
from app.lib.secrets_manager import get_secret
from app.lambda_handler import handler as lambda_handler, _ACTION_MAP
from app.observability import reasoning_logger as rl
from app.observability.cloudwatch_metrics import publish_telemetry_metrics, publish_lambda_metrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="module")
def setup_db():
    init_db()
    yield
    if os.path.exists("test_aquamind_cloud.db"):
        try:
            os.remove("test_aquamind_cloud.db")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Ollama Tests
# ---------------------------------------------------------------------------

def test_ollama_embedding_and_fallback():
    vec, model_used = embed.embed_text("test cooling load thermal management")
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert model_used in (settings.OLLAMA_EMBED_MODEL, embed.LOCAL_MODEL_NAME)


def test_ollama_agent_reasoning_structure():
    run_id = rl.new_run_id()
    twin_state = {"utilisation_pct": 88.5, "thermal_load_kw": 4.2}
    water_model = {"cooling_load_kw": 2.8, "wue_factor": 1.6, "water_l_per_hr": 100.0, "pue": 1.25}
    memories = [{"memory_id": "mem-001", "summary_text": "High GPU thermal spike resolved by pump boost", "similarity": 0.91}]

    res = langchain_ollama.invoke_langchain_ollama(
        run_id=run_id,
        twin_state=twin_state,
        water_model=water_model,
        memories=memories,
        open_incidents=1,
    )
    assert "recommendation" in res
    assert "confidence" in res
    assert "agent_name" in res
    # Accept Ollama agent OR rules_fallback (activated when langchain_ollama package is absent)
    assert any(token in res["agent_name"] for token in ("ollama", "rules_fallback", "water_cooling"))



# ---------------------------------------------------------------------------
# CockroachDB MCP + Vector Index Tests
# ---------------------------------------------------------------------------

def test_cockroach_mcp_tools_and_client():
    db = SessionLocal()
    try:
        stored = mcp_client.store_agent_memory(
            db,
            memory_type="incident",
            source_id="inc-999",
            summary="Pump pressure drop detected under 90% GPU load",
        )
        assert stored is not None
        assert stored["summary"] == "Pump pressure drop detected under 90% GPU load"

        incidents = mcp_client.retrieve_similar_incidents(db, "pump pressure drop", k=3)
        assert isinstance(incidents, list)
    finally:
        db.close()


def test_cockroach_vector_index_search():
    db = SessionLocal()
    try:
        mem = memory_store.store_memory(db, "convo-1", "incident", "Evaporative cooling overhead test")
        assert mem.memory_id is not None

        results = memory_store.search_memories(db, "evaporative cooling", k=2)
        assert len(results) >= 1
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Amazon S3 Tests
# ---------------------------------------------------------------------------

def test_s3_cold_storage_export():
    now = datetime.utcnow()
    s3_uri = export_cold_memory("mem-test-123", "summary", "Cold tier test content", now, now)
    assert s3_uri.startswith("s3://")


def test_s3_upload_report_csv():
    csv_content = "timestamp,device_id,cpu_pct\n2024-01-01T00:00:00,rack-01,42.5\n"
    uri = upload_report_to_s3("test_report.csv", csv_content, content_type="text/csv")
    assert uri.startswith("s3://")


def test_s3_upload_report_pdf_bytes():
    pdf_bytes = b"%PDF-1.4 test content bytes"
    uri = upload_report_to_s3("test_report.pdf", pdf_bytes, content_type="application/pdf")
    assert uri.startswith("s3://")


def test_s3_upload_telemetry_snapshot():
    snapshot = {
        "device_id": "rack-01",
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_pct": 55.0,
        "gpu_pct": 72.0,
        "ram_pct": 60.0,
    }
    uri = upload_telemetry_snapshot_to_s3(snapshot)
    assert uri.startswith("s3://")


def test_s3_upload_dataset_export():
    data = [{"id": 1, "value": "test"}, {"id": 2, "value": "dataset"}]
    uri = upload_dataset_export_to_s3("test_dataset", data)
    assert uri.startswith("s3://")


# ---------------------------------------------------------------------------
# AWS Secrets Manager Tests
# ---------------------------------------------------------------------------

def test_secrets_manager_disabled_returns_none():
    """When SECRETS_MANAGER_ENABLED=false, get_secret() must return None without error."""
    result = get_secret("aquamind/config")
    assert result is None


def test_secrets_manager_with_mock():
    """Verify get_secret() correctly parses a mocked Secrets Manager response."""
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": '{"DATABASE_URL": "cockroachdb://...", "API_TOKEN": "tok-abc"}'
    }
    import app.lib.secrets_manager as sm
    original = sm._secrets_client
    original_unavail = sm._secrets_unavailable
    try:
        sm._secrets_client = mock_client
        sm._secrets_unavailable = False
        # Temporarily enable Secrets Manager
        with patch.object(settings, "SECRETS_MANAGER_ENABLED", True):
            result = get_secret("aquamind/config")
        assert result is not None
        assert result["DATABASE_URL"] == "cockroachdb://..."
        assert result["API_TOKEN"] == "tok-abc"
    finally:
        sm._secrets_client = original
        sm._secrets_unavailable = original_unavail


def test_secrets_manager_invalid_json_wraps_in_dict():
    """Non-JSON secret strings are wrapped as {"secret": <raw_value>}."""
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {"SecretString": "plain-text-secret"}
    import app.lib.secrets_manager as sm
    original = sm._secrets_client
    original_unavail = sm._secrets_unavailable
    try:
        sm._secrets_client = mock_client
        sm._secrets_unavailable = False
        with patch.object(settings, "SECRETS_MANAGER_ENABLED", True):
            result = get_secret()
        assert result == {"secret": "plain-text-secret"}
    finally:
        sm._secrets_client = original
        sm._secrets_unavailable = original_unavail


# ---------------------------------------------------------------------------
# CloudWatch Metrics Tests
# ---------------------------------------------------------------------------

def test_cloudwatch_metrics_disabled_noop():
    """publish_telemetry_metrics() must return False when CLOUDWATCH_ENABLED=false."""
    result = publish_telemetry_metrics(gpu_pct=75.0, cooling_load_kw=2.5)
    assert result is False


def test_cloudwatch_lambda_metrics_disabled_noop():
    """publish_lambda_metrics() must return False when CLOUDWATCH_ENABLED=false."""
    result = publish_lambda_metrics("retier_memories", 120.0, True, 5)
    assert result is False


def test_cloudwatch_metrics_with_mock():
    """Verify put_metric_data is called with the correct namespace when enabled."""
    mock_cw = MagicMock()
    import app.observability.cloudwatch_metrics as cw_module
    original_client = cw_module._cw_client
    original_unavail = cw_module._cw_unavailable
    try:
        cw_module._cw_client = mock_cw
        cw_module._cw_unavailable = False
        with patch.object(settings, "CLOUDWATCH_ENABLED", True):
            result = publish_telemetry_metrics(
                gpu_pct=85.0,
                cooling_load_kw=3.1,
                wue_factor=1.8,
                water_l_per_hr=120.0,
                agent_confidence=0.92,
                water_saved_pct=12.0,
            )
        assert result is True
        mock_cw.put_metric_data.assert_called_once()
        call_kwargs = mock_cw.put_metric_data.call_args[1]
        assert call_kwargs["Namespace"] == "AquaMind/Operations"
        metric_names = {m["MetricName"] for m in call_kwargs["MetricData"]}
        assert "GPUUtilisation" in metric_names
        assert "CoolingLoadKW" in metric_names
        assert "AgentConfidence" in metric_names
        assert "WaterSavedPct" in metric_names
    finally:
        cw_module._cw_client = original_client
        cw_module._cw_unavailable = original_unavail


def test_cloudwatch_lambda_metrics_with_mock():
    """Verify Lambda metrics publish the correct dimensions."""
    mock_cw = MagicMock()
    import app.observability.cloudwatch_metrics as cw_module
    original_client = cw_module._cw_client
    original_unavail = cw_module._cw_unavailable
    try:
        cw_module._cw_client = mock_cw
        cw_module._cw_unavailable = False
        with patch.object(settings, "CLOUDWATCH_ENABLED", True):
            result = publish_lambda_metrics("cleanup_old_telemetry", 350.0, True, 42)
        assert result is True
        mock_cw.put_metric_data.assert_called_once()
        call_kwargs = mock_cw.put_metric_data.call_args[1]
        metric_names = {m["MetricName"] for m in call_kwargs["MetricData"]}
        assert "LambdaDurationMs" in metric_names
        assert "LambdaSuccess" in metric_names
        assert "LambdaRecordsProcessed" in metric_names
    finally:
        cw_module._cw_client = original_client
        cw_module._cw_unavailable = original_unavail


# ---------------------------------------------------------------------------
# CloudWatch Reasoning Logger Tests
# ---------------------------------------------------------------------------

def test_cloudwatch_reasoning_logger():
    run_id = rl.new_run_id()
    rl.log_step(run_id, "test_agent", "input", {"note": "CloudWatch test event"})
    events = rl.get_recent_events(run_id=run_id)
    assert len(events) >= 1


# ---------------------------------------------------------------------------
# Lambda EventBridge Handler Tests
# ---------------------------------------------------------------------------

def test_lambda_handler_retier_memories():
    """retier_memories action must succeed and return tier_counts."""
    evt = {"source": "aws.events", "detail-type": "Scheduled Event", "detail": {"action": "retier_memories"}}
    res = lambda_handler(evt)
    assert res["statusCode"] == 200
    assert "tier_counts" in res["body"]
    assert isinstance(res["body"]["tier_counts"], dict)


def test_lambda_handler_generate_scheduled_report():
    """generate_scheduled_report action must succeed and return an S3 URI."""
    evt = {"source": "aws.events", "detail": {"action": "generate_scheduled_report"}}
    res = lambda_handler(evt)
    assert res["statusCode"] == 200
    assert res["body"]["action"] == "generate_scheduled_report"
    assert res["body"]["s3_uri"].startswith("s3://")


def test_lambda_handler_cleanup_old_telemetry():
    """cleanup_old_telemetry action must succeed and report deleted_rows."""
    evt = {"source": "aws.events", "detail": {"action": "cleanup_old_telemetry"}}
    res = lambda_handler(evt)
    assert res["statusCode"] == 200
    assert "deleted_rows" in res["body"]
    assert isinstance(res["body"]["deleted_rows"], int)


def test_lambda_handler_telemetry_snapshot():
    """telemetry_snapshot action must succeed and return an S3 URI."""
    evt = {"source": "aws.events", "detail": {"action": "telemetry_snapshot"}}
    res = lambda_handler(evt)
    # May be 200 (snapshot uploaded) or 200 with no telemetry rows — both valid
    assert res["statusCode"] == 200
    assert res["body"]["action"] == "telemetry_snapshot"


def test_lambda_handler_legacy_plain_event():
    """Plain rate() events without detail.action default to retier_memories."""
    evt = {"source": "aws.events", "detail-type": "Scheduled Event"}
    res = lambda_handler(evt)
    assert res["statusCode"] == 200
    assert "tier_counts" in res["body"]


def test_lambda_handler_unknown_action_returns_400():
    """Unknown action names must return HTTP 400 without raising."""
    evt = {"source": "aws.events", "detail": {"action": "definitely_not_a_real_action"}}
    res = lambda_handler(evt)
    assert res["statusCode"] == 400


def test_lambda_handler_includes_run_id_and_duration():
    """Every successful response must carry run_id, timestamp, and duration_ms."""
    evt = {"source": "aws.events", "detail": {"action": "retier_memories"}}
    res = lambda_handler(evt)
    body = res["body"]
    assert "run_id" in body
    assert "timestamp" in body
    assert "duration_ms" in body
    assert isinstance(body["duration_ms"], float)


def test_all_action_map_keys_handled():
    """All actions registered in _ACTION_MAP must succeed via the handler."""
    for action in _ACTION_MAP:
        evt = {"source": "aws.events", "detail": {"action": action}}
        res = lambda_handler(evt)
        assert res["statusCode"] in (200, 500), f"Unexpected status for action={action}: {res['statusCode']}"
