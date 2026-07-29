"""
Water & Cooling Agent (SDD Phase 2, Section 6.1): "Reasons over the Water
Model's thermodynamic output (this is the Phase 1 single-agent logic,
promoted to a peer agent)."

Migration approach (Section 3.2): "Wrap existing call as the 'Water &
Cooling Agent'; add peers." This module does exactly that — it calls the
same app.agent.rules_fallback / app.agent.bedrock_client logic Phase 1
uses, unchanged.
"""
from typing import Dict

import phase2_distributed.common.pathsetup  # noqa: F401
from app.agent import bedrock_client, rules_fallback
from app.config import settings


class WaterCoolingAgent:
    name = "water_cooling"

    def run(self, context: Dict) -> Dict:
        twin_state_obj = context["twin_state_obj"]
        water_out = context["water_out"]
        memories = context["memories"]
        open_incidents = context.get("open_incidents", 0)

        if settings.BEDROCK_ENABLED:
            try:
                result = bedrock_client.invoke(
                    twin_state_obj.model_dump(), water_out, memories, open_incidents
                )
                result["agent"] = self.name
                return result
            except Exception:
                pass  # fall through to the deterministic rules fallback (FR-1.11 carried into Phase 2)

        result = rules_fallback.generate_recommendation(twin_state_obj, water_out, memories)
        result["agent"] = self.name
        return result
