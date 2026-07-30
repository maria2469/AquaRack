"""
Normaliser — raw OS-level metrics -> common JSON telemetry schema
shared with Phase 2 (SDD Section 14, FR-1.2).
"""
from datetime import datetime, timezone

import psutil


def _read_gpu_pct():
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        pynvml.nvmlShutdown()
        return float(util.gpu)
    except Exception:
        return None


def _read_fan_rpm():
    try:
        fans = psutil.sensors_fans()
        if not fans:
            return None
        for entries in fans.values():
            if entries:
                return int(entries[0].current)
    except Exception:
        pass
    return None


def _read_battery_pct():
    try:
        battery = psutil.sensors_battery()
        return float(battery.percent) if battery else None
    except Exception:
        return None


def collect_raw_reading() -> dict:
    cpu_pct = psutil.cpu_percent(interval=0.5)
    ram_pct = psutil.virtual_memory().percent
    try:
        disk = psutil.disk_io_counters()
        disk_io = float(disk.read_bytes + disk.write_bytes) if disk else None
    except Exception:
        disk_io = None
    return {
        "cpu_pct": cpu_pct,
        "gpu_pct": _read_gpu_pct(),
        "ram_pct": ram_pct,
        "disk_io": disk_io,
        "fan_rpm": _read_fan_rpm(),
        "battery_pct": _read_battery_pct(),
    }


def normalize(raw: dict, device_id: str, source: str = "laptop") -> dict:
    """Normalise into the shared TelemetryReading JSON schema (SDD Section 10.2)."""
    return {
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_pct": round(raw["cpu_pct"], 2),
        "gpu_pct": round(raw["gpu_pct"], 2) if raw.get("gpu_pct") is not None else None,
        "ram_pct": round(raw["ram_pct"], 2),
        "disk_io": raw.get("disk_io"),
        "fan_rpm": raw.get("fan_rpm"),
        "battery_pct": raw.get("battery_pct"),
        "source": source,
    }
