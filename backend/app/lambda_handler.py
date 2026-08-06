"""
AWS Lambda Serverless Handler (SDD Section 4.1 / Section 23).

Acts as the entry point when deployed as an AWS Lambda function.
Triggered by Amazon EventBridge scheduled rules to execute one of
several named actions. Supported ``detail.action`` values:

  retier_memories            — run the hot→warm→cold memory lifecycle job
                               and export newly-cold memories to S3.
  generate_scheduled_report  — generate a daily CSV telemetry summary
                               and upload it to S3.
  cleanup_old_telemetry      — delete telemetry rows older than the
                               configured retention window (90 days default).
  telemetry_snapshot         — fetch the latest telemetry row and upload
                               a point-in-time JSON snapshot to S3.
  resolve_episode_outcomes   — resolve all pending Episode rows (outcome_recorded_at
                               IS NULL, older than 15 min) and upsert StrategyScores.

Falls back to ``retier_memories`` for plain rate/cron events that carry
no ``detail.action`` key (backward-compatible with the v1 schedule).

Each action reports its execution time and result count to CloudWatch
via ``cloudwatch_metrics.publish_lambda_metrics()`` — silently skipped
when CLOUDWATCH_ENABLED=false (FR-1.11).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from app.config import settings
from app.memory_engine.retier_job import retier_memories
from app.memory_engine.outcome_watcher import resolve_pending_episodes
from app.observability import reasoning_logger as rl

logger = logging.getLogger("aquamind.lambda_handler")


# ---------------------------------------------------------------------------
# Individual action handlers
# ---------------------------------------------------------------------------

def _action_retier_memories(run_id: str, start: datetime) -> Dict[str, Any]:
    """Run memory re-tiering and S3 cold-tier export."""
    result = retier_memories(now=start)
    rl.log_step(run_id, "aws_lambda", "decision", {
        "action": "retier_memories",
        "status": "success",
        "counts": result,
        "s3_bucket": settings.S3_BUCKET,
    })
    return {
        "action": "retier_memories",
        "message": "Memory re-tiering complete",
        "tier_counts": result,
    }


def _action_generate_scheduled_report(run_id: str, start: datetime) -> Dict[str, Any]:
    """Generate a CSV telemetry report and upload it to S3."""
    try:
        from app.database import SessionLocal
        from app import models
        import csv
        import io
        from app.lib.s3_client import upload_report_to_s3

        db = SessionLocal()
        try:
            since = start - timedelta(hours=24)
            rows = db.query(models.Telemetry).filter(models.Telemetry.timestamp >= since).all()

            buf = io.StringIO()
            fieldnames = ["timestamp", "device_id", "cpu_pct", "gpu_pct", "ram_pct"]
            writer = csv.DictWriter(buf, fieldnames=fieldnames)
            writer.writeheader()
            for t in rows:
                writer.writerow({
                    "timestamp": t.timestamp.isoformat(),
                    "device_id": t.device_id,
                    "cpu_pct": t.cpu_pct,
                    "gpu_pct": t.gpu_pct or "",
                    "ram_pct": t.ram_pct,
                })

            filename = f"scheduled_report_{start.strftime('%Y%m%d_%H%M%S')}.csv"
            s3_uri = upload_report_to_s3(filename, buf.getvalue(), content_type="text/csv")
        finally:
            db.close()

        rl.log_step(run_id, "aws_lambda", "decision", {
            "action": "generate_scheduled_report",
            "rows": len(rows),
            "s3_uri": s3_uri,
        })
        return {
            "action": "generate_scheduled_report",
            "message": "Scheduled report uploaded",
            "rows": len(rows),
            "s3_uri": s3_uri,
        }
    except Exception as exc:
        logger.error(f"generate_scheduled_report failed: {exc}", exc_info=True)
        raise


def _action_cleanup_old_telemetry(run_id: str, start: datetime, retention_days: int = 90) -> Dict[str, Any]:
    """Delete telemetry rows older than retention_days."""
    try:
        from app.database import SessionLocal
        from app import models

        cutoff = start - timedelta(days=retention_days)
        db = SessionLocal()
        try:
            deleted = db.query(models.Telemetry).filter(models.Telemetry.timestamp < cutoff).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

        rl.log_step(run_id, "aws_lambda", "decision", {
            "action": "cleanup_old_telemetry",
            "deleted_rows": deleted,
            "cutoff": cutoff.isoformat(),
        })
        return {
            "action": "cleanup_old_telemetry",
            "message": f"Deleted {deleted} telemetry rows older than {retention_days} days",
            "deleted_rows": deleted,
        }
    except Exception as exc:
        logger.error(f"cleanup_old_telemetry failed: {exc}", exc_info=True)
        raise


def _action_telemetry_snapshot(run_id: str, start: datetime) -> Dict[str, Any]:
    """Fetch the latest telemetry row and upload a point-in-time snapshot to S3."""
    try:
        from app.database import SessionLocal
        from app import models
        from app.lib.s3_client import upload_telemetry_snapshot_to_s3

        db = SessionLocal()
        try:
            latest = db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).first()
            if latest is None:
                return {"action": "telemetry_snapshot", "message": "No telemetry rows found", "s3_uri": None}

            snapshot = {
                "device_id": latest.device_id,
                "timestamp": latest.timestamp.isoformat(),
                "cpu_pct": latest.cpu_pct,
                "gpu_pct": latest.gpu_pct,
                "ram_pct": latest.ram_pct,
                "snapshot_generated_at": start.isoformat(),
            }
            s3_uri = upload_telemetry_snapshot_to_s3(snapshot)
        finally:
            db.close()

        rl.log_step(run_id, "aws_lambda", "decision", {
            "action": "telemetry_snapshot",
            "device_id": snapshot["device_id"],
            "s3_uri": s3_uri,
        })
        return {
            "action": "telemetry_snapshot",
            "message": "Telemetry snapshot uploaded",
            "snapshot": snapshot,
            "s3_uri": s3_uri,
        }
    except Exception as exc:
        logger.error(f"telemetry_snapshot failed: {exc}", exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Action router
# ---------------------------------------------------------------------------

def _action_resolve_episode_outcomes(run_id: str, start: datetime) -> Dict[str, Any]:
    """Resolve pending episode outcomes and upsert StrategyScores."""
    result = resolve_pending_episodes(now=start)
    rl.log_step(run_id, "aws_lambda", "decision", {
        "action": "resolve_episode_outcomes",
        "status": "success",
        "resolved": result.get("resolved_episodes", 0),
    })
    return {
        "action": "resolve_episode_outcomes",
        "message": "Episode outcomes resolved",
        **result,
    }


_ACTION_MAP = {
    "retier_memories": _action_retier_memories,
    "generate_scheduled_report": _action_generate_scheduled_report,
    "cleanup_old_telemetry": _action_cleanup_old_telemetry,
    "telemetry_snapshot": _action_telemetry_snapshot,
    "resolve_episode_outcomes": _action_resolve_episode_outcomes,
}


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    AWS Lambda entry point function.

    EventBridge rule format expected::

        {
          "source": "aws.events",
          "detail-type": "Scheduled Event",
          "detail": {
            "action": "retier_memories"   # or any key in _ACTION_MAP
          }
        }

    Plain ``rate(...)`` events with no ``detail.action`` default to
    ``retier_memories`` for backward compatibility.
    """
    run_id = rl.new_run_id()
    start_time = datetime.utcnow()

    # Resolve action from EventBridge detail or legacy plain-rate event
    detail = event.get("detail") or {}
    action = detail.get("action", "retier_memories")

    rl.log_step(run_id, "aws_lambda", "input", {
        "event_source": event.get("source", "scheduled_event"),
        "action": action,
        "schedule": settings.LAMBDA_RETIER_SCHEDULE,
        "timestamp": start_time.isoformat(),
    })

    action_fn = _ACTION_MAP.get(action)
    if action_fn is None:
        msg = f"Unknown action '{action}'. Valid actions: {list(_ACTION_MAP)}"
        logger.error(msg)
        return {
            "statusCode": 400,
            "body": {"message": msg, "run_id": run_id, "timestamp": start_time.isoformat()},
        }

    try:
        body = action_fn(run_id, start_time)
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Publish Lambda execution metrics to CloudWatch (no-op if disabled).
        try:
            from app.observability.cloudwatch_metrics import publish_lambda_metrics
            records = (
                body.get("tier_counts", {}).get("exported", 0)
                or body.get("rows", 0)
                or body.get("deleted_rows", 0)
                or 0
            )
            publish_lambda_metrics(action=action, duration_ms=duration_ms, success=True, records_processed=records)
        except Exception:
            pass

        return {
            "statusCode": 200,
            "body": {
                **body,
                "run_id": run_id,
                "timestamp": start_time.isoformat(),
                "duration_ms": round(duration_ms, 2),
            },
        }

    except Exception as exc:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(f"Lambda handler execution failed (action={action}): {exc}", exc_info=True)
        rl.log_error(run_id, "aws_lambda", f"action={action} failed: {exc}")

        try:
            from app.observability.cloudwatch_metrics import publish_lambda_metrics
            publish_lambda_metrics(action=action, duration_ms=duration_ms, success=False)
        except Exception:
            pass

        return {
            "statusCode": 500,
            "body": {
                "message": "Lambda execution error",
                "action": action,
                "error": str(exc),
                "run_id": run_id,
                "timestamp": start_time.isoformat(),
            },
        }


if __name__ == "__main__":
    import json

    # Test each EventBridge action locally
    for act in _ACTION_MAP:
        print(f"\n--- Local test: action={act} ---")
        res = handler({"source": "local_test", "detail": {"action": act}})
        print(json.dumps(res, indent=2, default=str))
