"""
Telemetry Collector daemon (SDD Section 14).
Polls OS-level metrics at a configurable interval and pushes normalised
readings to the Ingestion API, buffering locally on failure.

Each reading is stamped with current real-world ambient weather (Open-
Meteo via app.services.weather_service, 15-minute cache) instead of
leaving weather_temp/humidity null and letting downstream consumers fall
back to hardcoded defaults.

Run directly:  python -m collector.run_collector
Or imported and started as a background thread by run.py.
"""
import logging
import time

from app.config import settings
from app.collector.normalizer import collect_raw_reading, normalize
from app.collector.local_queue import LocalQueue
from app.collector.client import IngestionClient
from app.services.weather_services import get_current_weather
from app.database import SessionLocal

logger = logging.getLogger("aquamind.collector")


def run(api_base_url: str = None, stop_event=None):
    api_base_url = api_base_url or f"http://{settings.API_HOST}:{settings.API_PORT}"
    queue = LocalQueue(settings.LOCAL_QUEUE_DB)
    client = IngestionClient(api_base_url, queue, api_token=settings.API_TOKEN)

    logger.info(
        "Telemetry collector starting: device=%s interval=%ss target=%s",
        settings.DEVICE_ID,
        settings.POLL_INTERVAL_SECONDS,
        api_base_url,
    )

    while True:
        if stop_event is not None and stop_event.is_set():
            logger.info("Collector stopping.")
            break
        try:
            raw = collect_raw_reading()
            reading = normalize(raw, device_id=settings.DEVICE_ID)

            # Attach real ambient weather. Uses a short-lived DB session
            # purely so the weather service can persist into the Weather
            # table on cache-miss; collector still works if this fails.
            try:
                db = SessionLocal()
                try:
                    weather = get_current_weather(db)
                finally:
                    db.close()
            except Exception as e:
                logger.warning("Weather lookup failed, telemetry sent without it: %s", e)
                weather = None

            if weather is not None:
                reading["weather_temp"] = weather["temperature"]
                reading["humidity"] = weather["humidity"]

            client.send(reading)
        except Exception as e:  # collector must never crash the demo
            logger.exception("Collector loop error: %s", e)
        time.sleep(settings.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()