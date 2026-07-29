"""
Single entrypoint for the Phase 1 demo: starts the FastAPI monolith and
the telemetry collector daemon together in one process, per SDD Section 3.1
("all execute in one process ... on the developer's laptop").

Usage:
    python run.py                 # API + collector (recommended)
    python run.py --no-collector  # API only
"""
import argparse
import threading
import time

import uvicorn

from app.config import settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-collector", action="store_true", help="Run API only")
    parser.add_argument("--host", default=settings.API_HOST)
    parser.add_argument("--port", type=int, default=settings.API_PORT)
    args = parser.parse_args()

    stop_event = threading.Event()

    if not args.no_collector:
        from collector.run_collector import run as run_collector

        def _start_collector():
            # give the API a moment to come up before the first POST
            time.sleep(2)
            run_collector(api_base_url=f"http://{args.host}:{args.port}", stop_event=stop_event)

        t = threading.Thread(target=_start_collector, daemon=True)
        t.start()
        print(f"[run.py] Telemetry collector started in background (device={settings.DEVICE_ID}).")

    print(f"[run.py] Starting AquaMind AI API on http://{args.host}:{args.port}  (dashboard at /)")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
