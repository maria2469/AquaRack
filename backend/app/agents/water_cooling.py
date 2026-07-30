"""
Water & Cooling Agent (SDD Phase 2, Section 6.1): "Reasons over the Water
Model's thermodynamic output (this is the Phase 1 single-agent logic,
promoted to a peer agent)."

Calls app.agents.langchain_ollama (Llama 3.1 / Qwen2.5) when OLLAMA_ENABLED=true,
falling back gracefully to deterministic rules_fallback on any error.
"""
from typing import Dict

from app.agents import langchain_ollama, rules_fallback
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

        if settings.OLLAMA_ENABLED:
            try:
                result = langchain_ollama.invoke_langchain_ollama(
                    run_id, twin_state_obj.model_dump(), water_out, memories, open_incidents, self.name
                )
                result["agent"] = self.name
                return result
            except Exception as exc:
                rl.log_error(run_id, self.name, f"Ollama/LangChain call failed, falling back to rules: {exc}")

        rl.log_step(run_id, self.name, "reasoning", {"note": "Using deterministic rules_fallback agent"})
        result = rules_fallback.generate_recommendation(twin_state_obj, water_out, memories)
        result["agent"] = self.name
        return result
