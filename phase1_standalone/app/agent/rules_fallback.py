"""
Deterministic rules-based AI Decision Agent fallback (SDD Section 5 / FR-1.11).
Keeps the recommendation loop closed with zero mandatory paid cloud
dependency. Reasons over the current TwinState + WaterModel output and any
retrieved memories, and produces the same OUTPUT SCHEMA the Bedrock-backed
agent would (SDD Section 16.1).
"""
from typing import List, Dict


def generate_recommendation(twin_state, water_out: Dict, memories: List[Dict]) -> Dict:
    util = twin_state.utilisation_pct
    cooling = water_out["cooling_load_kw"]
    wue = water_out["wue_factor"]
    water_rate = water_out["water_l_per_hr"]
    cited = [m["memory_id"] for m in memories[:3]]

    if util >= 85:
        rec = (
            f"Utilisation is critical at {util}%. Recommend immediately shedding "
            f"non-essential workload or increasing airflow/cooling capacity; "
            f"cooling load is {cooling}kW with an estimated water draw of "
            f"{water_rate} L/hr."
        )
        confidence = 0.88
        severity = "high"
    elif util >= 60:
        rec = (
            f"Utilisation is elevated at {util}%. Monitor closely and consider "
            f"pre-emptively increasing cooling capacity; current WUE is "
            f"{wue} L/kWh."
        )
        confidence = 0.72
        severity = "medium"
    else:
        rec = (
            f"Utilisation is nominal at {util}%. No cooling intervention needed; "
            f"current water usage effectiveness is {wue} L/kWh at "
            f"{water_rate} L/hr."
        )
        confidence = 0.6
        severity = "low"

    if memories:
        rec += (
            f" This aligns with {len(memories)} similar past reading(s) in memory "
            f"(top similarity {memories[0]['similarity']})."
        )

    rationale = (
        f"rules_fallback: severity={severity}; thresholds util>=85 (high), "
        f"util>=60 (medium), else low. thermal_load={twin_state.thermal_load_kw}kW, "
        f"cooling_load={cooling}kW."
    )

    return {
        "recommendation": rec,
        "confidence": confidence,
        "cited_memory_ids": cited,
        "rationale": rationale,
        "agent_name": "rules_fallback",
    }
