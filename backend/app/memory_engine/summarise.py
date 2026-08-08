"""
Memory Engine — Stage 2a: summarisation (SDD Section 11.2).
Deterministic and zero-cost, as required for Phase 1.

FIX: summarise_incident() previously returned f"[incident:{severity}] {description}".
If `description` is boilerplate (e.g. always "GPU 95%, High thermal load, Weather 39C")
across many incidents, the token sets are near-identical -- and under the local
hashed-BoW embedding (see embed.py), near-identical tokens produce near-identical
vectors regardless of severity/root-cause differences. That's the direct mechanism
behind flat 85%-ish similarity across unrelated queries.

These builders pull in whatever varying, specific fields are available (root cause,
rack, numeric readings, action taken) so summaries -- and therefore embeddings --
actually differ per incident. Call sites that build `description` upstream should
also avoid boilerplate; this only helps if the input text varies.
"""


def summarise_recommendation(twin_state, water_out: dict, rec_text: str) -> str:
    # Handle both dict and object twin_state
    if isinstance(twin_state, dict):
        utilisation = twin_state.get("utilisation_pct", 0)
        thermal_load = twin_state.get("thermal_load_kw", 0)
    else:
        utilisation = twin_state.utilisation_pct
        thermal_load = twin_state.thermal_load_kw
    
    return (
        f"[recommendation] utilisation={utilisation}% "
        f"thermal_load={thermal_load}kW "
        f"cooling_load={water_out['cooling_load_kw']}kW "
        f"wue={water_out['wue_factor']}L/kWh "
        f"water={water_out['water_l_per_hr']}L/hr :: {rec_text}"
    )


def summarise_incident(
    severity: str,
    description: str,
    root_cause: str | None = None,
    rack_id: str | None = None,
    created_at: str | None = None,
) -> str:
    """FIX: include root_cause/rack_id/created_at when available so incidents
    with similar boilerplate descriptions still produce distinguishable text
    (and therefore distinguishable embeddings)."""
    parts = [f"[incident:{severity}]"]
    if rack_id:
        parts.append(f"rack={rack_id}")
    if created_at:
        parts.append(f"at={created_at}")
    parts.append(description)
    if root_cause:
        parts.append(f"root_cause={root_cause}")
    return " ".join(parts)


def summarise_maintenance(mtype: str, notes: str) -> str:
    return f"[maintenance:{mtype}] {notes}"


def summarise_feedback(text: str) -> str:
    return f"[feedback] {text}"