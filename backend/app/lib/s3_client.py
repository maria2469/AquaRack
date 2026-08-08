"""
Amazon S3 client wrapper (SDD Section 12.2 — cold-tier memory export).

Real S3 destination for the "Retire" stage of memory lifecycle tiering,
replacing the local ./s3_lake/ JSON stand-in with an actual
`s3://<bucket>/<prefix>/...` object when S3_ENABLED=true and boto3 +
credentials are available. Falls back to the local JSON file automatically
otherwise — same dual-mode pattern as app.memory_engine.vector_index's
IS_COCKROACHDB check, so nothing breaks for anyone running without AWS
configured.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from app.config import settings

logger = logging.getLogger("aquamind.s3_client")

_s3_client = None
_s3_unavailable = False  # cached after first failure, avoids retrying boto3 import every call


def _get_s3_client():
    """Lazily creates and caches a boto3 S3 client. Returns None if boto3
    or credentials aren't available, so callers can fall back cleanly."""
    global _s3_client, _s3_unavailable
    if _s3_client is not None:
        return _s3_client
    if _s3_unavailable:
        return None
    try:
        import boto3

        # Use boto3's default credential chain (same as AWS CLI)
        # This will automatically check: env vars, credential file, config file, IAM role
        _s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
        return _s3_client
    except Exception as e:  # noqa: BLE001
        logger.warning(f"boto3 S3 client unavailable, using local fallback: {e}")
        _s3_unavailable = True
        return None


def _local_fallback_export(key: str, payload: Dict[str, Any]) -> str:
    """Writes the same payload to a local JSON file, mirroring the
    original _export_to_lake behaviour in retier_job.py."""
    dest_path = os.path.join(settings.S3_LOCAL_FALLBACK_DIR, key)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "w") as f:
        json.dump(payload, f, indent=2)
    return f"s3://{settings.S3_BUCKET}/{settings.S3_PREFIX}/{key}  (local fallback: {dest_path})"



def export_cold_memory(memory_id: str, mem_type: str, summary_text: str, created_at: datetime, now: datetime) -> str:
    """
    Exports one cold-tier memory to S3 (or the local fallback dir) and
    returns the s3:// URI to record in cdc_export_log. This is the
    function retier_job._export_to_lake should call instead of writing
    directly to disk.
    """
    key = f"cold_{memory_id}.json"
    payload = {
        "memory_id": memory_id,
        "type": mem_type,
        "summary_text": summary_text,
        "created_at": created_at.isoformat(),
        "exported_at": now.isoformat(),
    }

    if not settings.S3_ENABLED:
        return _local_fallback_export(key, payload)

    client = _get_s3_client()
    if client is None:
        return _local_fallback_export(key, payload)

    object_key = f"{settings.S3_PREFIX}/{key}"
    try:
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=object_key,
            Body=json.dumps(payload, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        return f"s3://{settings.S3_BUCKET}/{object_key}"
    except Exception as e:  # noqa: BLE001
        logger.error(f"S3 put_object failed: {e}. Falling back to local export.")
        return _local_fallback_export(key, payload)


def upload_report_to_s3(filename: str, content: bytes | str, content_type: str = "application/pdf") -> str:
    """
    Uploads a generated PDF/CSV report to Amazon S3 (s3://<bucket>/reports/<filename>)
    or falls back to local disk storage if S3 is disabled/unavailable.
    """
    key = f"reports/{filename}"
    body = content.encode("utf-8") if isinstance(content, str) else content

    if not settings.S3_ENABLED or _get_s3_client() is None:
        os.makedirs(os.path.join(settings.S3_LOCAL_FALLBACK_DIR, "reports"), exist_ok=True)
        local_path = os.path.join(settings.S3_LOCAL_FALLBACK_DIR, "reports", filename)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(local_path, mode) as f:
            f.write(content)
        return f"s3://{settings.S3_BUCKET}/{key} (local fallback: {local_path})"

    client = _get_s3_client()
    try:
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
        return f"s3://{settings.S3_BUCKET}/{key}"
    except Exception as e:
        logger.error(f"Failed to upload report to S3 ({e}), using local fallback.")
        local_path = os.path.join(settings.S3_LOCAL_FALLBACK_DIR, "reports", filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(local_path, mode) as f:
            f.write(content)
        return f"s3://{settings.S3_BUCKET}/{key} (local fallback: {local_path})"


def upload_telemetry_snapshot_to_s3(snapshot_data: Dict[str, Any]) -> str:
    """
    Uploads a live telemetry snapshot to Amazon S3 (s3://<bucket>/snapshots/...)
    """
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    key = f"snapshots/telemetry_{ts}.json"
    payload = json.dumps(snapshot_data, indent=2, default=str)

    if not settings.S3_ENABLED or _get_s3_client() is None:
        return _local_fallback_export(key, snapshot_data)

    try:
        _get_s3_client().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=payload.encode("utf-8"),
            ContentType="application/json",
        )
        return f"s3://{settings.S3_BUCKET}/{key}"
    except Exception as e:
        logger.error(f"S3 snapshot upload failed: {e}")
        return _local_fallback_export(key, snapshot_data)


def upload_dataset_export_to_s3(dataset_name: str, dataset_data: Any) -> str:
    """
    Uploads an exported dataset to Amazon S3 (s3://<bucket>/datasets/<dataset_name>.json)
    """
    key = f"datasets/{dataset_name}.json"
    payload = json.dumps({"dataset": dataset_name, "data": dataset_data, "exported_at": datetime.utcnow().isoformat()}, indent=2, default=str)

    if not settings.S3_ENABLED or _get_s3_client() is None:
        return _local_fallback_export(key, {"dataset": dataset_name, "data": dataset_data})

    try:
        _get_s3_client().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=payload.encode("utf-8"),
            ContentType="application/json",
        )
        return f"s3://{settings.S3_BUCKET}/{key}"
    except Exception as e:
        logger.error(f"S3 dataset export failed: {e}")
        return _local_fallback_export(key, {"dataset": dataset_name, "data": dataset_data})