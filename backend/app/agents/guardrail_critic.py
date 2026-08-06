"""
Guardrail / Critic Agent (SDD Phase 2, Section 6.1 / 18.2): Applies safety and policy
checks before a recommendation is persisted or surfaced.

Performs two checks deterministically with zero external dependency:
  (a) blocks denied topics outside the cooling/water domain, and
  (b) enforces that numeric claims in recommendations are traceable to CONTEXT or MEMORIES.
Every check outcome is pushed to the real-time reasoning log.
"""
import re
from typing import Dict

from app.observability import reasoning_logger as rl


class GuardrailCriticAgent:
    name = "guardrail_critic"

    # Denied-topic keywords (illustrative subset of Section 18.2's "unrelated
    # general chit-chat, unsafe operational instructions outside the
    # cooling/water domain").
    DENIED_TOPICS = ["politics", "medical diagnosis", "financial advice", "unrelated chit-chat"]

    _NUMBER_RE = re.compile(r"\d+\.?\d*")

    def run(self, context: Dict, draft: Dict) -> Dict:
        run_id = context.get("run_id") or rl.new_run_id()
        text = draft.get("recommendation", "")
        flags = []

        rl.log_step(run_id, self.name, "input", {"draft_recommendation": text, "draft_confidence": draft.get("confidence")})

        # Check 1: every numeric claim in the draft must be traceable back to
        # CONTEXT (twin_state/water_out) or MEMORIES (Section 18.2).
        traceable_source = " ".join(
            [
                str(context.get("twin_state", {})),
                str(context.get("water_out", {})),
                str(context.get("memories", [])),
            ]
        )
        allowed_numbers = set(self._NUMBER_RE.findall(traceable_source))
        claimed_numbers = set(self._NUMBER_RE.findall(text))
        untraceable = sorted(claimed_numbers - allowed_numbers)
        if untraceable:
            flags.append(f"untraceable_numeric_claims: {untraceable}")

        # Check 2: denied-topic keyword screen.
        lowered = text.lower()
        for topic in self.DENIED_TOPICS:
            if topic in lowered:
                flags.append(f"denied_topic_reference: '{topic}'")

        passed = len(flags) == 0
        confidence = draft.get("confidence", 0.5)
        confidence_adjusted = confidence if passed else round(max(0.1, confidence - 0.2), 3)

        rl.log_guardrail(run_id, self.name, passed, flags, confidence_adjusted)

        return {
            "agent": self.name,
            "passed": passed,
            "flags": flags,
            "confidence_adjusted": confidence_adjusted,
        }
