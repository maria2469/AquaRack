"""
Agent Reasoning Trace API (extends SDD Section 10 Reporting / Section 16
AI Decision Agent with real-time observability).

Exposes the live, step-by-step reasoning of the AI Decision Agent /
multi-agent orchestrator:
  - GET  /api/v1/agent/trace/recent   -> REST polling fallback (last N events)
  - GET  /api/v1/agent/trace/stream   -> Server-Sent Events, live feed
                                          (backend-ready for a future UI
                                          panel; also usable directly from
                                          the terminal via `curl -N`).

No frontend is added here — this is the backend contract a dashboard
would consume later (SDD "Future" section: real-time UI).
"""
import asyncio
import json

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from app.observability import reasoning_logger as rl

router = APIRouter(prefix="/api/v1/agent/trace", tags=["agent-trace"])


@router.get("/recent")
def recent(run_id: str | None = None, limit: int = Query(200, le=500)):
    """Poll the last N reasoning events (optionally filtered to one run_id)."""
    return {"events": rl.get_recent_events(run_id=run_id, limit=limit)}


@router.get("/stream")
async def stream(run_id: str | None = None):
    """
    Live Server-Sent Events stream of agent reasoning as it happens.
    Each event is a JSON object: {run_id, agent, stage, detail, ts, seq}.
    """

    async def event_generator():
        queue = await rl.subscribe()
        try:
            # Replay history for the current/latest run only so a client connecting
            # mid-run sees the lead-up without dumping old historical runs.
            recent_events = rl.get_recent_events(run_id=run_id, limit=50)
            if not run_id and recent_events:
                latest_run_id = recent_events[-1].get("run_id")
                recent_events = [e for e in recent_events if e.get("run_id") == latest_run_id]

            for evt in recent_events:
                yield {"event": "reasoning", "data": json.dumps(evt, default=str)}

            while True:
                evt = await queue.get()
                if run_id and evt.get("run_id") != run_id:
                    continue
                yield {"event": "reasoning", "data": json.dumps(evt, default=str)}
        except asyncio.CancelledError:
            raise
        finally:
            rl.unsubscribe(queue)

    return EventSourceResponse(event_generator())
