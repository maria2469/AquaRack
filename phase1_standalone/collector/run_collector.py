"""
Telemetry Collector daemon (SDD Section 14).
Polls OS-level metrics at a configurable interval and pushes normalised
readings to the Ingestion API, buffering locally on failure.

Run directly:  python -m collector.run_collector
Or imported and started as a background thread by run.py.
"""
import logging
import time

from app.config import settings
from collector.normalizer import collect_raw_reading, normalize
from collector.local_queue import LocalQueue
from collector.client import IngestionClient

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
            client.send(reading)
        except Exception as e:  # collector must never crash the demo
            logger.exception("Collector loop error: %s", e)
        time.sleep(settings.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
