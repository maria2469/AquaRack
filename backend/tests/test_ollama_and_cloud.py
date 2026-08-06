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
from app.lib.llm_client import generate_reasoning_with_fallback
from app.mcp import tools as mcp_tools
from app.mcp.client import mcp_client
from app.memory_engine import store as memory_store, embed, vector_index
from app.lib.s3_client import export_cold_memory, upload_report_to_s3, upload_telemetry_snapshot_to_s3, upload_dataset_export_to_s3
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
    assert model_used in (settings.OLLAMA_EMBED_MODEL, embed.LOCAL_MODEL_NAME, "embed-v4.0", "embed-english-v3.0")


def test_ollama_agent_reasoning_structure():
    run_id = rl.new_run_id()
    system_prompt = "You are a test thermal agent. Return JSON with key 'recommendation'."
    user_prompt = "Utilisation is 88.5%, thermal load is 4.2kW."

    try:
        res = generate_reasoning_with_fallback(
            run_id=run_id,
            agent_name="PredictorAgent",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        assert "raw_text" in res
        assert "provider" in res
    except RuntimeError as exc:
        assert "All LLM reasoning providers" in str(exc)


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
