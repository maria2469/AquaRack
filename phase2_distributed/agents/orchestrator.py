"""
Multi-agent Orchestrator (SDD Phase 2, Section 6): "Phase 2 replaces Phase
1's single AI Decision Agent with a governed multi-agent system ... so
that different reasoning concerns are separated, testable, and
independently improvable."

Flow (mirrors Figure 5 / Section 6.1):
  1. Memory/RAG Agent retrieves top-K similar past memories.
  2. Telemetry Analyst Agent flags anomalies/trends.
  3. Water & Cooling Agent produces the primary recommendation draft
     (the promoted Phase 1 single-agent logic).
  4. Capacity Planning Agent runs a lightweight what-if check.
  5. Guardrail/Critic Agent validates the aggregated draft before
     persistence (Section 18.2).

All agents call into the shared tool layer (Section 6.2) rather than the
DB directly.
"""
from typing import Dict

from sqlalchemy.orm import Session

from phase2_distributed.agents.capacity_planning import CapacityPlanningAgent
from phase2_distributed.agents.guardrail_critic import GuardrailCriticAgent
from phase2_distributed.agents.memory_rag import MemoryRAGAgent
from phase2_distributed.agents.telemetry_analyst import TelemetryAnalystAgent
from phase2_distributed.agents.water_cooling import WaterCoolingAgent


class Orchestrator:
    """Decomposes the incoming task, routes to specialised agents, aggregates
    their outputs (SDD Section 6.1, 'Orchestrator' role)."""

    def __init__(self):
        self.memory_rag = MemoryRAGAgent()
        self.telemetry_analyst = TelemetryAnalystAgent()
        self.water_cooling = WaterCoolingAgent()
        self.capacity_planning = CapacityPlanningAgent()
        self.guardrail = GuardrailCriticAgent()

    def route_task(self, db: Session, twin_state_obj, water_out: dict, open_incidents: int) -> Dict:
        twin_dict = twin_state_obj.model_dump()
        query_text = (
            f"utilisation {twin_dict['utilisation_pct']}% thermal load "
            f"{twin_dict['thermal_load_kw']}kW cooling load {water_out['cooling_load_kw']}kW"
        )

        trace = []

        memory_out = self.memory_rag.run(db, query_text, k=5)
        trace.append(memory_out)
        memories = memory_out["retrieved"]

        context = {
            "twin_state": twin_dict,
            "twin_state_obj": twin_state_obj,
            "water_out": water_out,
            "open_incidents": open_incidents,
            "memories": memories,
        }

        analyst_out = self.telemetry_analyst.run(context)
        trace.append(analyst_out)

        water_draft = self.water_cooling.run(context)
        trace.append(water_draft)

        capacity_out = self.capacity_planning.run(context)
        trace.append(capacity_out)

        aggregated_text = water_draft["recommendation"] + " " + capacity_out["advice"]
        if analyst_out.get("anomaly"):
            aggregated_text += " " + analyst_out["findings"][0]

        draft = {
            "recommendation": aggregated_text,
            "confidence": water_draft["confidence"],
            "cited_memory_ids": water_draft.get("cited_memory_ids", []),
            "rationale": water_draft.get("rationale", ""),
        }

        guardrail_out = self.guardrail.run(context, draft)
        trace.append(guardrail_out)

        final_confidence = (
            draft["confidence"] if guardrail_out["passed"] else guardrail_out["confidence_adjusted"]
        )

        return {
            "recommendation": aggregated_text,
            "confidence": final_confidence,
            "agent_name": "multi_agent_orchestrator",
            "cited_memory_ids": draft["cited_memory_ids"],
            "rationale": draft["rationale"] + f" | guardrail_passed={guardrail_out['passed']}",
            "agent_trace": trace,
        }


# Module-level singleton — stateless aside from immutable agent config, safe to share.
orchestrator = Orchestrator()
