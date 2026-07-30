"""
Amazon CloudWatch Custom Metrics Publisher (SDD Section 4.1 / Section 23 — Observability).

Publishes operational AquaMind telemetry metrics to CloudWatch for centralised
dashboarding and alerting — entirely optional and additive.  When CLOUDWATCH_ENABLED
is false, or boto3 / AWS credentials are absent, every call here is a no-op so agent
throughput is never impacted (FR-1.11: zero mandatory cloud dependency).

Metrics shipped per rack cycle
-------------------------------
  Namespace : AquaMind/Operations
  Dimensions: DeviceId (from AQUARACK_DEVICE_ID / settings.DEVICE_ID)

  Metric Name         Unit      Source
  ------------------  --------  -----------------------------------------------
  GPUUtilisation      Percent   telemetry.gpu_pct
  CoolingLoadKW       None      water_model.cooling_load_kw
  WaterSavedPct       Percent   derived from WUE vs baseline
  AgentConfidence     None      recommendation.confidence
  WUEFactor           None      water_model.wue_factor
  WaterLPerHr         None      water_model.water_l_per_hr

Usage::

    from app.observability.cloudwatch_metrics import publish_telemetry_metrics

    publish_telemetry_metrics(
        gpu_pct=telemetry.gpu_pct,
        cooling_load_kw=water_model["cooling_load_kw"],
        wue_factor=water_model["wue_factor"],
        water_l_per_hr=water_model["water_l_per_hr"],
        agent_confidence=rec["confidence"],
        water_saved_pct=water_saved,   # optional
    )
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.config import settings

logger = logging.getLogger("aquamind.cloudwatch_metrics")

# Lazy CloudWatch client — created once, reused.
_cw_client = None
_cw_unavailable = False
_NAMESPACE = "AquaMind/Operations"


def _get_cw_client():
    """Lazily initialise a boto3 CloudWatch client.  Returns None silently on any failure."""
    global _cw_client, _cw_unavailable
    if _cw_client is not None:
        return _cw_client
    if _cw_unavailable:
        return None
    try:
        import boto3

        _cw_client = boto3.client("cloudwatch", region_name=settings.AWS_REGION)
        return _cw_client
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"CloudWatch metrics client unavailable: {exc}")
        _cw_unavailable = True
        return None


def publish_telemetry_metrics(
    gpu_pct: Optional[float] = None,
    cooling_load_kw: Optional[float] = None,
    wue_factor: Optional[float] = None,
    water_l_per_hr: Optional[float] = None,
    agent_confidence: Optional[float] = None,
    water_saved_pct: Optional[float] = None,
    device_id: Optional[str] = None,
) -> bool:
    """
    Publish one rack-cycle's worth of operational metrics to CloudWatch.

    Parameters
    ----------
    gpu_pct          : GPU utilisation 0-100 (%)
    cooling_load_kw  : Computed thermal cooling load in kilowatts
    wue_factor       : Water Usage Effectiveness in L/kWh
    water_l_per_hr   : Estimated water consumption in litres per hour
    agent_confidence : AI decision agent confidence score 0-1
    water_saved_pct  : Estimated water saved vs baseline (%) — optional
    device_id        : Override the device dimension (defaults to settings.DEVICE_ID)

    Returns
    -------
    True  if the metrics were successfully published to CloudWatch.
    False if CloudWatch is disabled or unavailable (no exception raised).
    """
    if not settings.CLOUDWATCH_ENABLED:
        return False

    client = _get_cw_client()
    if client is None:
        return False

    dim = [{"Name": "DeviceId", "Value": device_id or settings.DEVICE_ID}]
    ts = datetime.utcnow()

    metric_data = []

    def _add(name: str, value: Optional[float], unit: str = "None") -> None:
        if value is not None:
            metric_data.append({
                "MetricName": name,
                "Dimensions": dim,
                "Timestamp": ts,
                "Value": float(value),
                "Unit": unit,
            })

    _add("GPUUtilisation", gpu_pct, "Percent")
    _add("CoolingLoadKW", cooling_load_kw)
    _add("WUEFactor", wue_factor)
    _add("WaterLPerHr", water_l_per_hr)
    _add("AgentConfidence", agent_confidence)
    _add("WaterSavedPct", water_saved_pct, "Percent")

    if not metric_data:
        return False

    try:
        # CloudWatch accepts at most 20 metric data points per put_metric_data call.
        for i in range(0, len(metric_data), 20):
            client.put_metric_data(Namespace=_NAMESPACE, MetricData=metric_data[i:i + 20])
        logger.debug(f"Published {len(metric_data)} metrics to CloudWatch ({_NAMESPACE})")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"CloudWatch put_metric_data failed: {exc}")
        return False


def publish_lambda_metrics(
    action: str,
    duration_ms: float,
    success: bool,
    records_processed: int = 0,
) -> bool:
    """
    Publish Lambda EventBridge invocation metrics to CloudWatch.

    Parameters
    ----------
    action            : EventBridge action name (e.g. 'retier_memories')
    duration_ms       : Wall-clock execution time in milliseconds
    success           : Whether the action completed without error
    records_processed : Number of records handled (e.g. memories exported)

    Returns
    -------
    True if published, False if CloudWatch disabled/unavailable.
    """
    if not settings.CLOUDWATCH_ENABLED:
        return False

    client = _get_cw_client()
    if client is None:
        return False

    dim = [
        {"Name": "DeviceId", "Value": settings.DEVICE_ID},
        {"Name": "Action", "Value": action},
    ]
    ts = datetime.utcnow()

    metric_data = [
        {
            "MetricName": "LambdaDurationMs",
            "Dimensions": dim,
            "Timestamp": ts,
            "Value": float(duration_ms),
            "Unit": "Milliseconds",
        },
        {
            "MetricName": "LambdaSuccess",
            "Dimensions": dim,
            "Timestamp": ts,
            "Value": 1.0 if success else 0.0,
            "Unit": "Count",
        },
        {
            "MetricName": "LambdaRecordsProcessed",
            "Dimensions": dim,
            "Timestamp": ts,
            "Value": float(records_processed),
            "Unit": "Count",
        },
    ]

    try:
        client.put_metric_data(Namespace=_NAMESPACE, MetricData=metric_data)
        logger.debug(f"Published Lambda metrics for action={action}")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"CloudWatch Lambda metrics failed: {exc}")
        return False
