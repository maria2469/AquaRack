"""
Telemetry Analyst Agent (SDD Phase 2, Section 6.1): "Detects anomalies and
trends in raw/normalised telemetry."
"""
from typing import Dict

from app.observability import reasoning_logger as rl


class TelemetryAnalystAgent:
    name = "telemetry_analyst"

    def run(self, context: Dict) -> Dict:
        run_id = context.get("run_id") or rl.new_run_id()
        twin = context["twin_state"]
        util = twin["utilisation_pct"]
        findings = []
        anomaly = False

        rl.log_step(run_id, self.name, "input", {"utilisation_pct": util})

        if util >= 90:
            findings.append(f"Utilisation spike detected ({util}%) — likely anomalous burst load.")
            anomaly = True
        elif util <= 2:
            findings.append(f"Utilisation near-zero ({util}%) — possible sensor stall or idle workload gap.")
            anomaly = True
        else:
            findings.append(f"Utilisation within the normal operating band ({util}%).")

        if context.get("open_incidents", 0) > 0:
            findings.append(f"{context['open_incidents']} open incident(s) currently unresolved on this rack.")

        rl.log_step(run_id, self.name, "decision", {"findings": findings, "anomaly": anomaly})

        return {"agent": self.name, "findings": findings, "anomaly": anomaly}
