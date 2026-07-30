"""
Capacity Planning Agent (SDD Phase 2, Section 6.1): "Runs digital-twin
what-if scenarios for capacity decisions."

Phase 1's DigitalTwinEngine already exposes utilisation/thermal-load
estimation as a reusable interface (SDD Section 12.1); this agent reuses
it to project a simple growth what-if scenario without needing a new
simulation job for every planning check.
"""
from typing import Dict

from app.observability import reasoning_logger as rl


class CapacityPlanningAgent:
    name = "capacity_planning"

    # Simple linear growth assumption for a lightweight "what-if" check;
    # a full scenario run instead submits a SimulationJob via
    # POST /api/v1/simulate/opendc with a higher-load workload_profile.
    GROWTH_FACTOR = 1.25

    def run(self, context: Dict) -> Dict:
        run_id = context.get("run_id") or rl.new_run_id()
        twin = context["twin_state"]
        util = twin["utilisation_pct"]
        projected = min(100.0, util * self.GROWTH_FACTOR)
        headroom_pct = round(100.0 - util, 2)

        rl.log_step(run_id, self.name, "input", {"utilisation_pct": util, "growth_factor": self.GROWTH_FACTOR})

        if headroom_pct < 15:
            advice = (
                f"Capacity headroom is only {headroom_pct}% at current load; recommend planning "
                f"additional rack capacity (or an OpenDC what-if simulation at a higher workload "
                f"profile) within the current planning cycle."
            )
            risk = "high"
        elif headroom_pct < 35:
            advice = (
                f"Capacity headroom is moderate ({headroom_pct}%); monitor growth trend and revisit "
                f"in the next planning cycle."
            )
            risk = "medium"
        else:
            advice = f"Capacity headroom is healthy ({headroom_pct}%); no near-term expansion required."
            risk = "low"

        rl.log_step(
            run_id, self.name, "decision",
            {"projected_utilisation_pct": round(projected, 2), "headroom_pct": headroom_pct, "risk": risk, "advice": advice},
        )

        return {
            "agent": self.name,
            "projected_utilisation_pct": round(projected, 2),
            "headroom_pct": headroom_pct,
            "risk": risk,
            "advice": advice,
        }
