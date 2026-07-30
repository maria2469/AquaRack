"""
Single entrypoint for AquaMind AI: starts the FastAPI app (telemetry,
digital twin, water model, memory engine, multi-agent AI decision system,
fleet dashboard, reports) and, optionally, the telemetry collector daemon.

Usage:
    python run.py                  # API + collector (recommended)
    python run.py --no-collector   # API only
    python run.py --port 8080
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
        from app.collector.run_collector import run as run_collector

        def _start_collector():
            time.sleep(2)  # let the API come up before the first POST
            run_collector(api_base_url=f"http://{args.host}:{args.port}", stop_event=stop_event)

        threading.Thread(target=_start_collector, daemon=True).start()
        print(f"[run.py] Telemetry collector started in background (device={settings.DEVICE_ID}).")

    print(f"[run.py] Starting AquaMind AI on http://{args.host}:{args.port}  (dashboard at /)")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
