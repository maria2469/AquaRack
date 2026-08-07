"""
Weather Service (fills the gap: Weather table exists but was never
populated; every consumer fell back to hardcoded 39C/62%).

Flow:
    Open-Meteo (no key required, uses WEATHER_LAT/WEATHER_LON)
        -> in-process 15-minute cache
        -> Weather table (persisted so history/telemetry joins work)
        -> returned to callers as {"temperature": ..., "humidity": ...}

Only falls back to settings.DEFAULT_AMBIENT_TEMP_C / DEFAULT_HUMIDITY_PCT
if WEATHER_ENABLED is false, no location is configured, or the API call
itself fails (network error, bad response, etc.) — never as the default
path.

LOGGING: every call logs which branch it took (cache hit / live fetch /
fallback) and the source of the returned reading, so you can grep logs to
confirm real weather is actually being used instead of assuming it.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone

import requests

from app import models
from app.config import settings

logger = logging.getLogger("aquamind.weather")

_CACHE_TTL = timedelta(minutes=15)
_cache_lock = threading.Lock()
_cache = {"value": None, "fetched_at": None}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _fallback(reason: str) -> dict:
    logger.warning(
        "WEATHER FALLBACK IN USE (reason=%s) — returning DEFAULT_AMBIENT_TEMP_C=%s / "
        "DEFAULT_HUMIDITY_PCT=%s, NOT real weather.",
        reason,
        settings.DEFAULT_AMBIENT_TEMP_C,
        settings.DEFAULT_HUMIDITY_PCT,
    )
    return {
        "temperature": settings.DEFAULT_AMBIENT_TEMP_C,
        "humidity": settings.DEFAULT_HUMIDITY_PCT,
        "source": "fallback_default",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _fetch_open_meteo() -> dict:
    lat = getattr(settings, "WEATHER_LAT", None)
    lon = getattr(settings, "WEATHER_LON", None)
    if lat is None or lon is None:
        raise ValueError("WEATHER_LAT/WEATHER_LON not configured")

    logger.info("Fetching live weather from Open-Meteo (lat=%s, lon=%s)", lat, lon)
    
    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m",
                "timezone": "auto",
            },
            timeout=10,  # Increased timeout for better reliability
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Validate response structure
        if "current" not in data:
            raise ValueError("Invalid Open-Meteo response structure")
            
        current = data["current"]
        if "temperature_2m" not in current or "relative_humidity_2m" not in current:
            raise ValueError("Missing required fields in Open-Meteo response")
            
        result = {
            "temperature": float(current["temperature_2m"]),
            "humidity": float(current["relative_humidity_2m"]),
            "source": "open-meteo",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Validate temperature and humidity ranges
        if not (-50 <= result["temperature"] <= 60):
            logger.warning(f"Unusual temperature value: {result['temperature']}°C")
        if not (0 <= result["humidity"] <= 100):
            logger.warning(f"Unusual humidity value: {result['humidity']}%")
            
        logger.info(
            "Open-Meteo returned REAL weather: temp=%.1f°C humidity=%.1f%%",
            result["temperature"],
            result["humidity"],
        )
        return result
        
    except requests.exceptions.Timeout:
        raise TimeoutError("Open-Meteo request timed out")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Open-Meteo request failed: {e}")
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"Invalid Open-Meteo response data: {e}")


def _persist(db, weather: dict) -> None:
    """Write the fetched reading into the Weather table so history/joins work."""
    try:
        row = models.Weather(
            ambient_temp=weather["temperature"],
            humidity=weather["humidity"],
            location=getattr(settings, "WEATHER_LOCATION_NAME", None),
            source=weather["source"],
        )
        db.add(row)
        db.commit()
        logger.info(
            "Persisted weather row to Weather table: weather_id=%s temp=%.1f humidity=%.1f source=%s",
            row.weather_id,
            row.ambient_temp,
            row.humidity,
            row.source,
        )
    except Exception as e:
        logger.warning("Failed to persist weather reading: %s", e)
        db.rollback()


def get_current_weather(db=None, force_refresh: bool = False) -> dict:
    """
    Returns {"temperature": float, "humidity": float, "source": str,
    "fetched_at": iso str}. Cached for 15 minutes in-process. Persists
    fresh reads to the Weather table when a db session is provided.

    `source` in the return value tells you definitively whether this was
    real: "open-meteo" = real, "fallback_default" = NOT real.
    """
    if not getattr(settings, "WEATHER_ENABLED", False):
        return _fallback("WEATHER_ENABLED is false")

    with _cache_lock:
        if (
            not force_refresh
            and _cache["value"] is not None
            and datetime.now(timezone.utc) - _cache["fetched_at"] < _CACHE_TTL
        ):
            cached = _cache["value"]
            age_s = (datetime.now(timezone.utc) - _cache["fetched_at"]).total_seconds()
            logger.debug(
                "Weather cache hit (age=%.0fs, source=%s, temp=%.1f, humidity=%.1f)",
                age_s,
                cached["source"],
                cached["temperature"],
                cached["humidity"],
            )
            return cached

        try:
            weather = _fetch_open_meteo()
        except Exception as e:
            logger.error("Open-Meteo fetch failed (%s), using fallback instead of real weather.", e)
            weather = _fallback(f"open-meteo request failed: {e}")

        _cache["value"] = weather
        _cache["fetched_at"] = datetime.now(timezone.utc)

    if db is not None and weather.get("source") == "open-meteo":
        _persist(db, weather)

    return weather