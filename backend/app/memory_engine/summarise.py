"""
Memory Engine — Stage 2a: template-based summarisation (SDD Section 11.2).
Deterministic and zero-cost, as required for Phase 1.
"""


def summarise_recommendation(twin_state, water_out: dict, rec_text: str) -> str:
    return (
        f"[recommendation] utilisation={twin_state.utilisation_pct}% "
        f"thermal_load={twin_state.thermal_load_kw}kW "
        f"cooling_load={water_out['cooling_load_kw']}kW "
        f"wue={water_out['wue_factor']}L/kWh "
        f"water={water_out['water_l_per_hr']}L/hr :: {rec_text}"
    )


def summarise_incident(severity: str, description: str) -> str:
    return f"[incident:{severity}] {description}"


def summarise_maintenance(mtype: str, notes: str) -> str:
    return f"[maintenance:{mtype}] {notes}"


def summarise_feedback(text: str) -> str:
    return f"[feedback] {text}"
