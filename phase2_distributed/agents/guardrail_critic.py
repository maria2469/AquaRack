"""
Guardrail / Critic Agent (SDD Phase 2, Section 6.1 / 18.2): "Applies
Bedrock Guardrails and policy checks before a recommendation is persisted
or surfaced."

In AWS, this maps onto Amazon Bedrock Guardrails, configured to (a) block
denied topics and (b) enforce that numeric claims are traceable to CONTEXT
or MEMORIES (Section 18.2). This local implementation performs the same
two checks deterministically, with zero external dependency, so the
guardrail step is always exercised in the demo (mirrors Phase 1's
zero-mandatory-cloud-dependency principle carried into Phase 2).
"""
import re
from typing import Dict


class GuardrailCriticAgent:
    name = "guardrail_critic"

    # Denied-topic keywords (illustrative subset of Section 18.2's "unrelated
    # general chit-chat, unsafe operational instructions outside the
    # cooling/water domain").
    DENIED_TOPICS = ["politics", "medical diagnosis", "financial advice", "unrelated chit-chat"]

    _NUMBER_RE = re.compile(r"\d+\.?\d*")

    def run(self, context: Dict, draft: Dict) -> Dict:
        text = draft.get("recommendation", "")
        flags = []

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

        return {
            "agent": self.name,
            "passed": passed,
            "flags": flags,
            "confidence_adjusted": confidence_adjusted,
        }
