"""
Ingestion API client: posts telemetry, buffering to the LocalQueue on
failure and replaying oldest-first once the API is reachable again.
"""
import logging

import requests

logger = logging.getLogger("aquamind.collector")


class IngestionClient:
    def __init__(self, base_url: str, queue, api_token: str = "", device_id: str = ""):
        self.base_url = base_url.rstrip("/")
        self.queue = queue
        self.api_token = api_token
        self.device_id = device_id

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_token:
            h["Authorization"] = f"Bearer {self.api_token}"
        if self.device_id:
            h["X-Device-ID"] = self.device_id
        return h

    def _post(self, payload: dict) -> bool:
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/telemetry",
                json=payload,
                headers=self._headers(),
                timeout=10,  # Increased from 5 to 10 seconds
            )
            return resp.status_code == 202
        except requests.RequestException as e:
            logger.warning("Ingestion API unreachable: %s", e)
            return False

    def send(self, payload: dict):
        """Try to flush the queue first (preserving order), then send this reading."""
        self.flush_queue()
        if not self._post(payload):
            logger.info("Buffering reading locally (API unreachable)")
            self.queue.enqueue(payload)

    def flush_queue(self):
        batch = self.queue.peek_batch(limit=100)
        for row_id, payload in batch:
            if self._post(payload):
                self.queue.remove(row_id)
            else:
                break  # preserve order; stop at first failure
