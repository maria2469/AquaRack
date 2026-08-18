"""
Weather Service (fills the gap: Weather table exists but was never
populated; every consumer fell back to hardcoded 39C/62%).

Flow:
    Open-Meteo (no key required, uses device-specific location or WEATHER_LAT/WEATHER_LON)
        -> in-process 15-minute cache per location
        -> Weather table (persisted so history/telemetry joins work)
        -> returned to callers as {"temperature": ..., "humidity": ...}

Location-Aware:
    - Device-specific locations take priority over cached telemetry weather
    - Location change detection triggers fresh weather fetches
    - Distance-based cache invalidation for mobile devices

Only falls back to settings.DEFAULT_AMBIENT_TEMP_C / DEFAULT_HUMIDITY_PCT
if WEATHER_ENABLED is false, no location is configured, or the API call
itself fails (network error, bad response, etc.) — never as the default
path.

LOGGING: every call logs which branch it took (cache hit / live fetch /
fallback) and the source of the returned reading, so you can grep logs to
confirm real weather is actually being used instead of assuming it.
"""
import logging
import math
import threading
from datetime import datetime, timedelta, timezone

import requests

from app import models
from app.config import settings

logger = logging.getLogger("aquamind.weather")

_CACHE_TTL = timedelta(minutes=15)
_CACHE_TTL_DISTANCE_KM = 50  # Force refresh if location changes by 50km
_cache_lock = threading.Lock()
_cache = {}  # Device-specific cache: {(lat, lon): {"value": None, "fetched_at": None, "location": (lat, lon)}}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    Returns distance in kilometers.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')

    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of Earth in kilometers
    r = 6371
    return c * r


def _should_refresh_cache(cache_key: tuple, new_lat: float, new_lon: float) -> bool:
    """
    Determine if weather cache should be refreshed based on location change.
    Returns True if location changed significantly (>50km) or cache is expired.
    """
    if cache_key not in _cache:
        return True

    cache_entry = _cache[cache_key]
    if cache_entry["value"] is None:
        return True

    # Check time-based expiration
    age = datetime.now(timezone.utc) - cache_entry["fetched_at"]
    if age > _CACHE_TTL:
        return True

    # Check location-based expiration
    cached_location = cache_entry.get("location")
    if cached_location and cached_location != (None, None):
        cached_lat, cached_lon = cached_location
        if cached_lat and cached_lon and new_lat and new_lon:
            distance = _haversine_distance(cached_lat, cached_lon, new_lat, new_lon)
            if distance > _CACHE_TTL_DISTANCE_KM:
                logger.info(
                    f"Location change detected: {distance:.1f}km (threshold: {_CACHE_TTL_DISTANCE_KM}km) - forcing weather refresh"
                )
                return True

    return False


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


def _fetch_open_meteo(lat: float = None, lon: float = None) -> dict:
    # Use provided coordinates or fall back to config defaults
    if lat is None or lon is None:
        lat = getattr(settings, "WEATHER_LAT", None)
        lon = getattr(settings, "WEATHER_LON", None)
        if lat is None or lon is None:
            raise ValueError("WEATHER_LAT/WEATHER_LON not configured and no device location provided")

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


def get_current_weather(db=None, force_refresh: bool = False, lat: float = None, lon: float = None, ignore_cached_telemetry: bool = False) -> dict:
    """
    Returns {"temperature": float, "humidity": float, "source": str,
    "fetched_at": iso str}. Cached for 15 minutes in-process per location.
    Persists fresh reads to the Weather table when a db session is provided.

    Location-Aware Behavior:
    - Device-specific location takes priority over cached telemetry weather
    - Location changes >50km trigger fresh weather fetch
    - Falls back to config defaults if no location provided

    `source` in the return value tells you definitively whether this was
    real: "open-meteo" = real, "fallback_default" = NOT real.

    Args:
        db: Optional database session for persistence
        force_refresh: Bypass cache and fetch fresh data
        lat: Optional latitude for device-specific weather (overrides config)
        lon: Optional longitude for device-specific weather (overrides config)
        ignore_cached_telemetry: Skip telemetry-attached weather and use location-based API
    """
    if not getattr(settings, "WEATHER_ENABLED", False):
        return _fallback("WEATHER_ENABLED is false")

    # Use device-specific coordinates or fall back to config defaults
    cache_key = (lat, lon) if lat and lon else ("default", "default")

    with _cache_lock:
        # Initialize cache entry if not exists
        if cache_key not in _cache:
            _cache[cache_key] = {"value": None, "fetched_at": None, "location": (lat, lon)}

        # Check if we should refresh based on location change or time
        should_refresh = force_refresh or _should_refresh_cache(cache_key, lat, lon)

        if not should_refresh and _cache[cache_key]["value"] is not None:
            cached = _cache[cache_key]["value"]
            age_s = (datetime.now(timezone.utc) - _cache[cache_key]["fetched_at"]).total_seconds()
            logger.debug(
                "Weather cache hit for %s (age=%.0fs, source=%s, temp=%.1f, humidity=%.1f)",
                cache_key,
                age_s,
                cached["source"],
                cached["temperature"],
                cached["humidity"],
            )
            return cached

        try:
            weather = _fetch_open_meteo(lat, lon)
        except Exception as e:
            logger.error("Open-Meteo fetch failed (%s), using fallback instead of real weather.", e)
            weather = _fallback(f"open-meteo request failed: {e}")

        _cache[cache_key]["value"] = weather
        _cache[cache_key]["fetched_at"] = datetime.now(timezone.utc)
        _cache[cache_key]["location"] = (lat, lon)

    if db is not None and weather.get("source") == "open-meteo":
        _persist(db, weather)

    return weather