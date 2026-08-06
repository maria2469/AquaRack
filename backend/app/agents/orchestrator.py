"""
Multi-agent Orchestrator (SDD Phase 2, Section 6): Governed multi-agent system
where different reasoning concerns are separated, testable, and independently improvable.

LangGraph 5-Node State Machine Flow:
  1. Monitor Agent — Ingests telemetry & performs hybrid vector search.
  2. Predictor Agent — Predicts thermal/power risks via Ollama/Groq (llm_client).
  3. Optimizer Agent — Formulates optimal cooling & energy saving strategy.
  4. Action Agent — Validates cluster health & Guardrail Critic, executes memory storage.
  5. Explainer Agent — Assembles operator-facing response and decision audit.

All agents call into the shared MCP tool layer rather than the DB directly.
Every step is pushed to the real-time reasoning log tagged with a shared run_id.
"""
from typing import Dict

from sqlalchemy.orm import Session

from app.agents.guardrail_critic import GuardrailCriticAgent
from app.observability import reasoning_logger as rl


class Orchestrator:
    """Decomposes the incoming task, routes to specialised agents via LangGraph state machine."""

    def __init__(self):
        from app.agents.langgraph_workflow import langgraph_runner
        self.langgraph_runner = langgraph_runner

    def route_task(self, db: Session, twin_state_obj, water_out: dict, open_incidents: int) -> Dict:
        return self.langgraph_runner.run(db, twin_state_obj, water_out, open_incidents)


# Module-level singleton — stateless aside from immutable agent config, safe to share.
orchestrator = Orchestrator()


