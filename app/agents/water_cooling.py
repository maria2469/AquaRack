"""
Water & Cooling Agent (SDD Phase 2, Section 6.1): "Reasons over the Water
Model's thermodynamic output (this is the Phase 1 single-agent logic,
promoted to a peer agent)."

Migration approach (Section 3.2): "Wrap existing call as the 'Water &
Cooling Agent'; add peers." This module does exactly that — it calls the
same app.agent.rules_fallback / app.agent.langchain_bedrock logic Phase 1
uses, unchanged, with each step pushed to the real-time reasoning log.
"""
from typing import Dict

  # noqa: F401
from app.agents import langchain_bedrock, rules_fallback
from app.config import settings
from app.observability import reasoning_logger as rl


class WaterCoolingAgent:
    name = "water_cooling"

    def run(self, context: Dict) -> Dict:
        twin_state_obj = context["twin_state_obj"]
        water_out = context["water_out"]
        memories = context["memories"]
        open_incidents = context.get("open_incidents", 0)
        run_id = context.get("run_id") or rl.new_run_id()

        rl.log_step(
            run_id, self.name, "input",
            {
                "utilisation_pct": twin_state_obj.utilisation_pct,
                "thermal_load_kw": twin_state_obj.thermal_load_kw,
                "cooling_load_kw": water_out.get("cooling_load_kw"),
                "memories_count": len(memories),
                "open_incidents": open_incidents,
            },
        )

        if settings.BEDROCK_ENABLED:
            try:
                result = langchain_bedrock.invoke_langchain(
                    run_id, twin_state_obj.model_dump(), water_out, memories, open_incidents, self.name
                )
                result["agent"] = self.name
                return result
            except Exception as exc:
                rl.log_error(run_id, self.name, f"Bedrock/LangChain call failed, falling back to rules: {exc}")
                # fall through to the deterministic rules fallback (FR-1.11 carried into Phase 2)

        rl.log_step(run_id, self.name, "reasoning", {"note": "Using deterministic rules_fallback agent"})
        result = rules_fallback.generate_recommendation(twin_state_obj, water_out, memories)
        result["agent"] = self.name
        return result
