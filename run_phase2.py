"""
Single entrypoint for the combined Phase 1 + Phase 2 demo (SDD Phase 2,
Section 3: "Phase 2 extends Phase 1 rather than replacing it").

Usage:
    python run_phase2.py                  # combined API + fleet-aware dashboard
    python run_phase2.py --port 8080
    python run_phase2.py --with-collector # also starts the Phase 1 laptop telemetry collector

For the "true microservices" story (five independently runnable
processes matching the Phase 2 architecture diagram), see
phase2_distributed/docker-compose.yml or run each
phase2_distributed/services/*/main.py directly.
"""
import argparse
import os
import sys
import threading
import time

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--with-collector",
        action="store_true",
        help="Also start the Phase 1 laptop telemetry collector in the background",
    )
    args = parser.parse_args()

    import uvicorn

    if args.with_collector:
        _phase1_dir = os.path.join(_REPO_ROOT, "phase1_standalone")
        if _phase1_dir not in sys.path:
            sys.path.insert(0, _phase1_dir)

        from app.config import settings
        from collector.run_collector import run as run_collector

        stop_event = threading.Event()

        def _start_collector():
            time.sleep(2)
            run_collector(api_base_url=f"http://{args.host}:{args.port}", stop_event=stop_event)

        threading.Thread(target=_start_collector, daemon=True).start()
        print(f"[run_phase2.py] Telemetry collector started in background (device={settings.DEVICE_ID}).")

    print(
        f"[run_phase2.py] Starting AquaMind AI Phase 1+2 combined gateway on "
        f"http://{args.host}:{args.port}  (dashboard at /)"
    )
    uvicorn.run("phase2_distributed.gateway.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
