"""
LangGraph Multi-Agent State Machine Workflow for RackPulse.
Decomposes operational decision making into distinct agent nodes:
  Monitor -> Predictor -> Optimizer -> Action -> Explainer

Demonstrates stateful agent transitions, MCP tool usage (hybrid vector search, memory persistence, ccloud health),
and local Ollama Qwen reasoning with Groq fallback.
"""

import logging
from typing import Dict, Any, List, Optional, TypedDict
from sqlalchemy.orm import Session

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

from app.lib.llm_client import generate_reasoning_with_fallback
from app.mcp.tools import (
    retrieve_similar_incidents,
    retrieve_similar_episodes,
    hybrid_search_incidents,
    store_agent_memory,
)
from app.mcp.ccloud_tools import ccloud_cluster_health
from app.agents.guardrail_critic import GuardrailCriticAgent
from app.observability import reasoning_logger as rl

logger = logging.getLogger("aquamind.langgraph_workflow")


class AgentState(TypedDict):
    run_id: str
    db: Any  # Session
    twin_dict: Dict[str, Any]
    water_out: Dict[str, Any]
    open_incidents: int
    retrieved_memories: List[Dict[str, Any]]
    episode_priors: List[Dict[str, Any]]   # Task 7: similar historical episodes
    cluster_health: Dict[str, Any]
    predicted_risks: Dict[str, Any]
    optimization_plan: Dict[str, Any]
    action_result: Dict[str, Any]
    explanation: Dict[str, Any]
    agent_trace: List[Dict[str, Any]]
    final_output: Dict[str, Any]


def monitor_node(state: AgentState) -> AgentState:
    """Node 1: Monitor Agent — Analyzes real-time metrics, performs hybrid vector search,
    and retrieves similar historical episodes for RL priors (Task 7)."""
    run_id = state["run_id"]
    db = state["db"]
    twin = state["twin_dict"]
    water = state["water_out"]

    rl.log_step(run_id, "MonitorAgent", "input", {"note": "Ingesting telemetry and retrieving context"})

    query_text = (
        f"utilisation {twin.get('utilisation_pct')}% thermal load {twin.get('thermal_load_kw')}kW "
        f"cooling load {water.get('cooling_load_kw')}kW"
    )

    rack_id = twin.get("rack_id", "rack-01")
    search_res = hybrid_search_incidents(db, query_text=query_text, rack_id=rack_id, k=5)
    memories = search_res.get("matches", [])

    # Task 7 — Episode-first retrieval: fetch historically similar episodes as RL priors
    try:
        episode_priors = retrieve_similar_episodes(db, query_text=query_text, rack_id=rack_id, k=5)
    except Exception as ep_exc:
        logger.warning("Episode retrieval failed: %s", ep_exc)
        episode_priors = []

    step_info = {
        "agent": "MonitorAgent",
        "query": query_text,
        "retrieved_memories_count": len(memories),
        "retrieved_episodes_count": len(episode_priors),
        "retrieval_method": search_res.get("retrieval_method"),
    }
    state["agent_trace"].append(step_info)
    state["retrieved_memories"] = memories
    state["episode_priors"] = episode_priors
    rl.log_step(run_id, "MonitorAgent", "reasoning", step_info)
    return state


def predictor_node(state: AgentState) -> AgentState:
    """Node 2: Predictor Agent — Predicts thermal/power risks using Ollama Qwen (or Groq fallback)."""
    run_id = state["run_id"]
    twin = state["twin_dict"]
    water = state["water_out"]
    memories = state["retrieved_memories"]

    system_prompt = (
        "You are the Risk Predictor Agent for data-centre thermal & energy management.\n"
        "Predict operational risks (thermal runaway, WUE spikes, capacity overload) based on telemetry and past incident memories.\n"
        "Respond ONLY with a valid JSON object containing:\n"
        '  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"\n'
        '  "primary_risk": string summary\n'
        '  "predicted_pue_impact": float\n'
    )

    user_prompt = (
        f"Telemetry: Utilisation={twin.get('utilisation_pct')}%, ThermalLoad={twin.get('thermal_load_kw')}kW, "
        f"CoolingLoad={water.get('cooling_load_kw')}kW.\n"
        f"Past Incidents: {memories[:3]}"
    )

    try:
        res = generate_reasoning_with_fallback(run_id, "PredictorAgent", system_prompt, user_prompt)
        parsed = res.get("parsed_json", {})
        predictions = {
            "risk_level": parsed.get("risk_level", "MEDIUM"),
            "primary_risk": parsed.get("primary_risk", "Moderate thermal load increase detected"),
            "predicted_pue_impact": float(parsed.get("predicted_pue_impact", 1.15)),
            "llm_provider": res.get("provider"),
        }
    except Exception as exc:
        logger.warning("PredictorAgent LLM failed (%s), using rule-based prediction.", exc)
        predictions = {
            "risk_level": "HIGH" if twin.get("utilisation_pct", 0) > 85 else "MEDIUM",
            "primary_risk": "Utilisation threshold exceeded",
            "predicted_pue_impact": 1.25 if twin.get("utilisation_pct", 0) > 85 else 1.10,
            "llm_provider": "rules_fallback",
        }

    state["predicted_risks"] = predictions
    state["agent_trace"].append({"agent": "PredictorAgent", "predictions": predictions})
    rl.log_step(run_id, "PredictorAgent", "reasoning", predictions)
    return state


def optimizer_node(state: AgentState) -> AgentState:
    """Node 3: Optimizer Agent — Computes optimal cooling strategy.
    Task 5: logs 2 candidate strategies + rejected alternative.
    Task 6: blends LLM confidence 60% with StrategyScore prior 40%.
    Task 7: incorporates episode priors into the prompt.
    """
    run_id = state["run_id"]
    db = state["db"]
    twin = state["twin_dict"]
    water = state["water_out"]
    risks = state["predicted_risks"]
    episode_priors = state.get("episode_priors", [])

    # Task 6: query StrategyScore for prior confidence on candidate strategies
    strategy_prior_note = ""
    try:
        from app.models_ext import StrategyScore
        scores = db.query(StrategyScore).order_by(StrategyScore.confidence.desc()).limit(3).all()
        if scores:
            strategy_prior_note = (
                "Historical strategy scores (action: confidence): "
                + ", ".join(f"{s.strategy_key}={s.confidence:.2f}" for s in scores)
            )
    except Exception as sc_exc:
        logger.debug("StrategyScore query failed: %s", sc_exc)

    # Task 7: episode prior summary for prompt
    episode_note = ""
    if episode_priors:
        ep_strs = [
            f"'{e['action_taken']}' success={e['success']} water_delta={e['water_delta_pct']}%"
            for e in episode_priors[:3]
        ]
        episode_note = f"\nSimilar past episodes: {'; '.join(ep_strs)}."

    system_prompt = (
        "You are the Cooling & Power Optimizer Agent.\n"
        "Propose TWO candidate strategies and select the best one.\n"
        "Respond ONLY with a valid JSON object containing:\n"
        '  "recommendation": string (chosen strategy)\n'
        '  "confidence": float between 0 and 1\n'
        '  "expected_water_saving": float\n'
        '  "rationale": string\n'
        '  "alternative": string (the other candidate strategy you rejected)\n'
    )

    user_prompt = (
        f"Risk Level: {risks.get('risk_level')}, Primary Risk: {risks.get('primary_risk')}.\n"
        f"Current Cooling: {water.get('cooling_load_kw')}kW, WUE Factor: {water.get('wue_factor', 0.4)}.\n"
        + (f"{strategy_prior_note}\n" if strategy_prior_note else "")
        + episode_note
    )

    llm_confidence = 0.88
    alternative = None
    try:
        res = generate_reasoning_with_fallback(run_id, "OptimizerAgent", system_prompt, user_prompt)
        parsed = res.get("parsed_json", {})
        llm_confidence = float(parsed.get("confidence", 0.88))
        alternative = parsed.get("alternative")
        optimization = {
            "recommendation": parsed.get("recommendation", "Increase liquid cooling flow by 12% to maintain thermal equilibrium."),
            "confidence": llm_confidence,
            "expected_water_saving": float(parsed.get("expected_water_saving", 15.5)),
            "rationale": parsed.get("rationale", "Proactive cooling adjustment prevents thermal throttle."),
        }
    except Exception:
        optimization = {
            "recommendation": "Increase liquid cooling flow by 10% to prevent thermal overhead spike.",
            "confidence": 0.75,
            "expected_water_saving": 10.0,
            "rationale": "Rules fallback: steady cooling increase for safe operation.",
        }
        llm_confidence = 0.75

    # Task 6: 60/40 blend with StrategyScore
    try:
        from app.models_ext import StrategyScore
        key = optimization["recommendation"][:80]  # truncate for key
        score = db.get(StrategyScore, key)
        if score and (score.success_count + score.failure_count) >= 3:
            blended = round(0.6 * llm_confidence + 0.4 * score.confidence, 3)
            optimization["confidence"] = blended
            optimization["rationale"] += f" [StrategyScore blended: {blended:.2f}]"
    except Exception as blend_exc:
        logger.debug("StrategyScore blending skipped: %s", blend_exc)

    # Task 5: log rejected alternative
    alternatives_rejected = [alternative] if alternative else []
    rl.log_step(
        run_id, "OptimizerAgent", "reasoning",
        {**optimization, "alternative": alternative},
        alternatives_rejected=alternatives_rejected,
    )

    state["optimization_plan"] = optimization
    state["agent_trace"].append({"agent": "OptimizerAgent", "plan": optimization, "alternative": alternative})
    return state


def action_node(state: AgentState) -> AgentState:
    """Node 4: Action Agent — Validates cluster health & safety guardrails, executes state mutation & memory storage via MCP."""
    run_id = state["run_id"]
    db = state["db"]
    opt = state["optimization_plan"]
    twin = state["twin_dict"]

    # Check CockroachDB cluster health via ccloud MCP tool
    cluster_status = ccloud_cluster_health()

    # Validate with Guardrail Critic
    critic = GuardrailCriticAgent()
    draft = {
        "recommendation": opt["recommendation"],
        "confidence": opt["confidence"],
        "cited_memory_ids": [m.get("id") for m in state["retrieved_memories"] if m.get("id")],
        "rationale": opt["rationale"],
    }
    critic_res = critic.run({"twin_state": twin, "open_incidents": state["open_incidents"]}, draft)

    passed = critic_res.get("passed", True)
    final_conf = opt["confidence"] if passed else critic_res.get("confidence_adjusted", 0.5)

    # Persist agent memory via MCP tool
    stored_mem = {}
    if db:
        try:
            summary = f"Action: {opt['recommendation']} | Expected Saving: {opt['expected_water_saving']}L/hr | Confidence: {final_conf}"
            stored_mem = store_agent_memory(db, memory_type="recommendation", source_id=run_id, summary=summary)
        except Exception as exc:
            logger.warning("ActionAgent memory persistence failed: %s", exc)

    action_result = {
        "cluster_health": cluster_status,
        "guardrail_passed": passed,
        "final_confidence": final_conf,
        "stored_memory": stored_mem,
    }

    state["action_result"] = action_result
    state["agent_trace"].append({"agent": "ActionAgent", "result": action_result})
    rl.log_step(run_id, "ActionAgent", "reasoning", action_result)
    return state


def reflect_node(state: AgentState) -> AgentState:
    """Node 5 (Task 6): Reflect Agent — Creates an initial Episode row capturing the
    decision context immediately after action execution. Outcome fields (water_delta_pct,
    temp_delta_c, success, reward) are left NULL and resolved asynchronously by
    outcome_watcher.resolve_pending_episodes() ~15 minutes later."""
    run_id = state["run_id"]
    db = state["db"]
    opt = state["optimization_plan"]
    act = state["action_result"]
    twin = state["twin_dict"]
    water = state["water_out"]

    try:
        from app.models_ext import Episode
        import uuid as _uuid
        ep = Episode(
            episode_id=str(_uuid.uuid4()),
            run_id=run_id,
            rack_id=twin.get("rack_id"),
            recommendation_id=act.get("stored_memory", {}).get("id"),
            telemetry_snapshot={
                k: twin.get(k)
                for k in ["cpu_pct", "gpu_pct", "gpu_temp", "ram_pct", "utilisation_pct", "thermal_load_kw"]
                if twin.get(k) is not None
            },
            water_snapshot={
                k: water.get(k)
                for k in ["water_l_per_hr", "cooling_load_kw", "wue_factor", "pue"]
                if water.get(k) is not None
            },
            action_taken=opt.get("recommendation", "")[:200],
            action_params={"expected_water_saving": opt.get("expected_water_saving")},
            confidence_at_decision=act.get("final_confidence", opt.get("confidence", 0.5)),
        )
        if db:
            db.add(ep)
            db.commit()
        rl.log_step(run_id, "ReflectAgent", "reasoning", {
            "episode_id": ep.episode_id,
            "note": "Episode created; outcome pending outcome_watcher resolution.",
        })
        state["agent_trace"].append({"agent": "ReflectAgent", "episode_id": ep.episode_id})
    except Exception as exc:
        logger.warning("ReflectAgent episode creation failed: %s", exc)

    return state


def explainer_node(state: AgentState) -> AgentState:
    """Node 5: Explainer Agent — Assembles comprehensive operator-facing response and decision audit."""
    run_id = state["run_id"]
    opt = state["optimization_plan"]
    act = state["action_result"]
    memories = state["retrieved_memories"]

    cited_ids = [m["id"] for m in memories if "id" in m]

    explanation_text = (
        f"Recommendation: {opt['recommendation']} "
        f"(Confidence: {act['final_confidence']:.2f}, Rationale: {opt['rationale']}). "
        f"Validated by Guardrail Critic ({'PASSED' if act['guardrail_passed'] else 'ADJUSTED'})."
    )

    final_output = {
        "run_id": run_id,
        "recommendation": explanation_text,
        "confidence": act["final_confidence"],
        "agent_name": "langgraph_multi_agent",
        "cited_memory_ids": cited_ids,
        "rationale": f"LangGraph State Machine (Monitor->Predictor->Optimizer->Action->Explainer) | {opt['rationale']}",
        "agent_trace": state["agent_trace"],
        "expected_water_saving": opt.get("expected_water_saving", 0.0),
    }

    state["agent_trace"].append({"agent": "ExplainerAgent", "explanation": explanation_text})
    state["final_output"] = final_output
    rl.log_decision(run_id, "LangGraphOrchestrator", explanation_text, act["final_confidence"], final_output["rationale"], cited_ids)
    return state


class LangGraphWorkflowRunner:
    """Executes the 6-node multi-agent pipeline:
    Monitor -> Predictor -> Optimizer -> Action -> Reflect -> Explainer
    """

    def __init__(self):
        if HAS_LANGGRAPH:
            graph = StateGraph(AgentState)
            graph.add_node("monitor", monitor_node)
            graph.add_node("predictor", predictor_node)
            graph.add_node("optimizer", optimizer_node)
            graph.add_node("action", action_node)
            graph.add_node("reflect", reflect_node)   # Task 6
            graph.add_node("explainer", explainer_node)

            graph.set_entry_point("monitor")
            graph.add_edge("monitor", "predictor")
            graph.add_edge("predictor", "optimizer")
            graph.add_edge("optimizer", "action")
            graph.add_edge("action", "reflect")        # Task 6: action -> reflect
            graph.add_edge("reflect", "explainer")     # Task 6: reflect -> explainer
            graph.add_edge("explainer", END)

            self.app = graph.compile()
        else:
            self.app = None

    def run(self, db: Session, twin_state_obj, water_out: dict, open_incidents: int) -> Dict[str, Any]:
        run_id = rl.new_run_id()
        twin_dict = twin_state_obj.model_dump()

        initial_state: AgentState = {
            "run_id": run_id,
            "db": db,
            "twin_dict": twin_dict,
            "water_out": water_out,
            "open_incidents": open_incidents,
            "retrieved_memories": [],
            "episode_priors": [],            # Task 7
            "cluster_health": {},
            "predicted_risks": {},
            "optimization_plan": {},
            "action_result": {},
            "explanation": {},
            "agent_trace": [],
            "final_output": {},
        }

        if self.app:
            final_state = self.app.invoke(initial_state)
            return final_state["final_output"]

        # Clean fallback runner if langgraph package is absent
        s1 = monitor_node(initial_state)
        s2 = predictor_node(s1)
        s3 = optimizer_node(s2)
        s4 = action_node(s3)
        s5 = reflect_node(s4)       # Task 6
        s6 = explainer_node(s5)
        return s6["final_output"]


langgraph_runner = LangGraphWorkflowRunner()
