"""
Real-time Agent Reasoning Logger (SDD Section 5/6 — "AI Decision Agent" /
"Orchestrator"; extends Section 10 Reporting with a live reasoning trace).

Goal: every step an agent takes — what it was given, what it decided, how
confident it is, and why — is:
  1. written to structured logs (console + aquamind_reasoning.log) AS IT
     HAPPENS, not after the fact, so `tail -f` shows live agent thinking.
  2. pushed into an in-memory ring buffer + asyncio pub/sub so a FastAPI
     endpoint can stream it live (SSE) to a future UI, without needing a
     message broker for the local/demo deployment.

This is intentionally dependency-free (stdlib logging + asyncio) so it
works identically in Phase 1 (monolith) and Phase 2 (distributed
services) — each process just imports `reasoning_logger` and calls
`log_step(...)`.

Usage:
    from app.observability.reasoning_logger import log_step, log_decision

    log_step(run_id, agent="water_cooling", stage="input",
              detail={"utilisation_pct": 91.2, "cooling_load_kw": 3.1})
    log_step(run_id, agent="water_cooling", stage="reasoning",
              detail={"note": "Calling Bedrock via LangChain..."})
    log_decision(run_id, agent="water_cooling",
                 recommendation="...", confidence=0.88,
                 rationale="...", cited_memory_ids=[...])
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any, Deque, Dict, List, Optional

# ---------------------------------------------------------------------------
# Structured stdlib logger — always-on, human- and machine-readable.
# Separate log file from the general app log so `tail -f aquamind_reasoning.log`
# gives a clean, dedicated view of agent thinking in real time.
# ---------------------------------------------------------------------------
_LOG_PATH = os.environ.get("AQUAMIND_REASONING_LOG", "aquamind_reasoning.log")

reasoning_logger = logging.getLogger("aquamind.reasoning")
if not reasoning_logger.handlers:
    reasoning_logger.setLevel(logging.INFO)
    _fmt = logging.Formatter("%(asctime)s %(message)s")

    _fh = logging.FileHandler(_LOG_PATH)
    _fh.setFormatter(_fmt)
    reasoning_logger.addHandler(_fh)

    _sh = logging.StreamHandler()
    _sh.setFormatter(_fmt)
    reasoning_logger.addHandler(_sh)

    # Optional third handler: ships the same live reasoning trace to
    # CloudWatch Logs. Purely additive — file + stdout handlers above are
    # unaffected either way. Gated behind settings.CLOUDWATCH_ENABLED and
    # wrapped defensively so a missing `watchtower` package, missing AWS
    # credentials, or a permissions error never breaks agent execution;
    # it just logs a warning locally and continues with file+stdout only.
    if os.environ.get("AQUAMIND_SKIP_CLOUDWATCH") != "1":
        try:
            from app.config import settings

            if settings.CLOUDWATCH_ENABLED:
                import watchtower

                _cw = watchtower.CloudWatchLogHandler(
                    log_group=settings.CLOUDWATCH_LOG_GROUP,
                    stream_name=settings.CLOUDWATCH_LOG_STREAM,
                )
                _cw.setFormatter(_fmt)
                reasoning_logger.addHandler(_cw)
        except Exception as _cw_exc:  # noqa: BLE001
            reasoning_logger.warning(f"CloudWatch handler not attached: {_cw_exc}")

    reasoning_logger.propagate = False


# ---------------------------------------------------------------------------
# Live event bus: ring buffer (for late subscribers / REST polling) +
# asyncio.Queue fan-out (for SSE streaming to a future UI).
# ---------------------------------------------------------------------------
_MAX_BUFFER = 500
_event_buffer: Deque[Dict[str, Any]] = deque(maxlen=_MAX_BUFFER)
_subscribers: List["asyncio.Queue[Dict[str, Any]]"] = []


@dataclass
class ReasoningEvent:
    run_id: str
    agent: str
    stage: str  # "input" | "reasoning" | "tool_call" | "decision" | "guardrail" | "error"
    detail: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    seq: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_seq_counter = 0


def new_run_id() -> str:
    """Call once per top-level agent invocation (e.g. one /recommend request)."""
    return str(uuid.uuid4())


def _publish(event: ReasoningEvent) -> None:
    global _seq_counter
    _seq_counter += 1
    event.seq = _seq_counter

    _event_buffer.append(event.to_dict())

    # Write live to logs — this is what makes it visible "in real time" in
    # the terminal / log file, not just retrievable after the fact.
    reasoning_logger.info(json.dumps(event.to_dict(), default=str))

    # Fan out to any live SSE subscribers (dropped silently if the queue is
    # full / nobody is listening — this must never block agent execution).
    for q in list(_subscribers):
        try:
            q.put_nowait(event.to_dict())
        except asyncio.QueueFull:
            pass


def log_step(run_id: str, agent: str, stage: str, detail: Optional[Dict[str, Any]] = None) -> None:
    """Log one reasoning step in real time (input received, tool called, etc.)."""
    _publish(ReasoningEvent(run_id=run_id, agent=agent, stage=stage, detail=detail or {}))


def log_decision(
    run_id: str,
    agent: str,
    recommendation: str,
    confidence: float,
    rationale: str,
    cited_memory_ids: Optional[List[str]] = None,
) -> None:
    """Log a final agent decision — always the last event for that agent in a run."""
    _publish(
        ReasoningEvent(
            run_id=run_id,
            agent=agent,
            stage="decision",
            detail={
                "recommendation": recommendation,
                "confidence": confidence,
                "rationale": rationale,
                "cited_memory_ids": cited_memory_ids or [],
            },
        )
    )


def log_guardrail(run_id: str, agent: str, passed: bool, flags: List[str], confidence_adjusted: float) -> None:
    _publish(
        ReasoningEvent(
            run_id=run_id,
            agent=agent,
            stage="guardrail",
            detail={"passed": passed, "flags": flags, "confidence_adjusted": confidence_adjusted},
        )
    )


def log_error(run_id: str, agent: str, error: str) -> None:
    _publish(ReasoningEvent(run_id=run_id, agent=agent, stage="error", detail={"error": error}))


def get_recent_events(run_id: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """REST-polling fallback: recent events, optionally filtered to one run."""
    events = list(_event_buffer)
    if run_id:
        events = [e for e in events if e["run_id"] == run_id]
    return events[-limit:]


async def subscribe() -> "asyncio.Queue[Dict[str, Any]]":
    """Register a new SSE subscriber queue. Caller must unsubscribe() when done."""
    q: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    return q


def unsubscribe(q: "asyncio.Queue[Dict[str, Any]]") -> None:
    if q in _subscribers:
        _subscribers.remove(q)