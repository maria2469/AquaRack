"""
LangGraph Multi-Agent State Machine Workflow for AquaRack.
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
    use_memory: bool
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
    twin = state["twin_dict"]  # Changed from twin to twin_dict since we return dict now
    water = state["water_out"]

    use_memory = state.get("use_memory", True)
    
    # Agent thinking step 1: Initial assessment
    thinking_steps = [
        f"🔍 STEP 1: Analyzing current telemetry state",
        f"   - Utilisation: {twin.get('utilisation_pct')}%",
        f"   - Thermal Load: {twin.get('thermal_load_kw')}kW", 
        f"   - Cooling Load: {water.get('cooling_load_kw')}kW",
        f"   - Water Usage: {water.get('water_l_per_hr')}L/hr"
    ]
    
    rl.log_step(
        run_id,
        "MonitorAgent",
        "thinking",
        {"steps": thinking_steps, "phase": "initial_assessment"}
    )

    rl.log_step(
        run_id,
        "MonitorAgent",
        "input",
        {"note": "Ingesting telemetry" + (" and retrieving context" if use_memory else " (memory disabled)")},
    )

    query_text = (
        f"utilisation {twin.get('utilisation_pct')}% thermal load {twin.get('thermal_load_kw')}kW "
        f"cooling load {water.get('cooling_load_kw')}kW"
    )

    rack_id = twin.get("rack_id", "rack-01")
    
    # Agent thinking step 2: Memory retrieval decision
    thinking_steps.append(f"🔍 STEP 2: Memory retrieval {'enabled' if use_memory else 'disabled'}")
    if use_memory:
        thinking_steps.append(f"   - Query: {query_text}")
        thinking_steps.append(f"   - Target rack: {rack_id}")
    
    rl.log_step(
        run_id,
        "MonitorAgent", 
        "thinking",
        {"steps": thinking_steps, "phase": "memory_decision"}
    )
    
    if not use_memory:
        memories = []
        episode_priors = []
        step_info = {
            "agent": "MonitorAgent",
            "query": query_text,
            "retrieved_memories_count": 0,
            "retrieved_episodes_count": 0,
            "retrieval_method": "disabled",
            "thinking": "Memory retrieval disabled - proceeding with telemetry-only analysis"
        }
    else:
        # Agent thinking step 3: Tool execution
        thinking_steps.append(f"🔍 STEP 3: Executing hybrid vector search tool")
        rl.log_step(
            run_id,
            "MonitorAgent",
            "tool_call",
            {"tool": "hybrid_search_incidents", "query": query_text, "rack_id": rack_id}
        )
        
        search_res = hybrid_search_incidents(db, query_text=query_text, rack_id=rack_id, k=5)
        memories = search_res.get("matches", [])
        
        thinking_steps.append(f"   - Retrieved {len(memories)} similar incidents")
        thinking_steps.append(f"   - Search method: {search_res.get('retrieval_method')}")

        # Task 7 — Episode-first retrieval: fetch historically similar episodes as RL priors
        thinking_steps.append(f"🔍 STEP 4: Retrieving similar historical episodes for RL priors")
        try:
            episode_priors = retrieve_similar_episodes(db, query_text=query_text, rack_id=rack_id, k=5)
            thinking_steps.append(f"   - Retrieved {len(episode_priors)} similar episodes")
        except Exception as ep_exc:
            logger.warning("Episode retrieval failed: %s", ep_exc)
            episode_priors = []
            thinking_steps.append(f"   - Episode retrieval failed: {ep_exc}")

        step_info = {
            "agent": "MonitorAgent",
            "query": query_text,
            "retrieved_memories_count": len(memories),
            "retrieved_episodes_count": len(episode_priors),
            "retrieval_method": search_res.get("retrieval_method"),
            "thinking": "\n".join(thinking_steps),
            "retrieved_memories": memories[:3],  # Include sample memories
            "retrieved_episodes": episode_priors[:3]  # Include sample episodes
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

    # Agent thinking process
    thinking_steps = [
        f"🧠 STEP 1: Assessing current system state",
        f"   - Utilisation: {twin.get('utilisation_pct')}%",
        f"   - Thermal Load: {twin.get('thermal_load_kw')}kW",
        f"   - Cooling Load: {water.get('cooling_load_kw')}kW",
        f"   - WUE Factor: {water.get('wue_factor', 0.4)}",
        f"🧠 STEP 2: Analyzing retrieved incidents",
        f"   - Available incidents: {len(memories)}",
        f"   - Recent patterns: {[m.get('summary', 'N/A')[:50] for m in memories[:2]]}"
    ]
    
    rl.log_step(run_id, "PredictorAgent", "thinking", {"steps": thinking_steps, "phase": "assessment"})

    system_prompt = (
        "You are the Risk Predictor Agent for data-centre thermal & energy management.\n"
        "Predict operational risks (thermal runaway, WUE spikes, capacity overload) based on telemetry and past incident memories.\n"
        "Respond ONLY with a valid JSON object containing:\n"
        '  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"\n'
        '  "primary_risk": string summary\n'
        '  "predicted_pue_impact": float\n'
        '  "reasoning": detailed step-by-step analysis\n'
    )

    user_prompt = (
        f"Telemetry: Utilisation={twin.get('utilisation_pct')}%, ThermalLoad={twin.get('thermal_load_kw')}kW, "
        f"CoolingLoad={water.get('cooling_load_kw')}kW.\n"
        f"Past Incidents: {memories[:3]}\n\n"
        "Please analyze the current situation and provide detailed reasoning for your risk assessment."
    )

    rl.log_step(run_id, "PredictorAgent", "input", {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "note": "Analyzing telemetry for risk prediction"
    })

    thinking_steps.append(f"🧠 STEP 3: Invoking LLM for risk analysis")
    thinking_steps.append(f"   - Agent: PredictorAgent")
    thinking_steps.append(f"   - Input: Telemetry + {len(memories)} incidents")
    
    rl.log_step(run_id, "PredictorAgent", "thinking", {"steps": thinking_steps, "phase": "llm_invocation"})

    try:
        res = generate_reasoning_with_fallback(run_id, "PredictorAgent", system_prompt, user_prompt)
        parsed = res.get("parsed_json", {})
        
        thinking_steps.append(f"🧠 STEP 4: Processing LLM response")
        thinking_steps.append(f"   - Provider: {res.get('provider')}")
        thinking_steps.append(f"   - Risk Level: {parsed.get('risk_level', 'MEDIUM')}")
        thinking_steps.append(f"   - Primary Risk: {parsed.get('primary_risk', 'N/A')}")
        thinking_steps.append(f"   - PUE Impact: {parsed.get('predicted_pue_impact', 1.15)}")
        
        predictions = {
            "risk_level": parsed.get("risk_level", "MEDIUM"),
            "primary_risk": parsed.get("primary_risk", "Moderate thermal load increase detected"),
            "predicted_pue_impact": float(parsed.get("predicted_pue_impact", 1.15)),
            "reasoning": parsed.get("reasoning", "Standard risk assessment based on current metrics"),
            "llm_provider": res.get("provider"),
            "llm_raw_response": res.get("raw_text", ""),
            "thinking": "\n".join(thinking_steps),
        }
    except Exception as exc:
        logger.error("PredictorAgent LLM failed (%s), no fallback available - check Ollama/Groq configuration", exc)
        thinking_steps.append(f"❌ LLM FAILED: {exc}")
        raise RuntimeError(f"PredictorAgent LLM reasoning failed: {exc}. Please check Ollama and Groq configuration.")

    state["predicted_risks"] = predictions
    state["agent_trace"].append({"agent": "PredictorAgent", "predictions": predictions, "thinking": "\n".join(thinking_steps)})
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
    use_memory = state.get("use_memory", True)
    episode_priors = state.get("episode_priors", []) if use_memory else []

    # Agent thinking process
    thinking_steps = [
        f"⚙️ STEP 1: Analyzing risk assessment",
        f"   - Risk Level: {risks.get('risk_level')}",
        f"   - Primary Risk: {risks.get('primary_risk')}",
        f"   - PUE Impact: {risks.get('predicted_pue_impact')}",
        f"⚙️ STEP 2: Reviewing current cooling performance",
        f"   - Cooling Load: {water.get('cooling_load_kw')}kW",
        f"   - WUE Factor: {water.get('wue_factor', 0.4)}",
        f"   - Water Usage: {water.get('water_l_per_hr')}L/hr"
    ]
    
    rl.log_step(run_id, "OptimizerAgent", "thinking", {"steps": thinking_steps, "phase": "risk_analysis"})

    strategy_prior_note = ""
    episode_note = ""
    manual_note = ""

    if use_memory:
        # Task 6: query StrategyScore for prior confidence on candidate strategies
        thinking_steps.append(f"⚙️ STEP 3: Retrieving historical strategy performance")
        try:
            from app.models_ext import StrategyScore
            scores = db.query(StrategyScore).order_by(StrategyScore.confidence.desc()).limit(3).all()
            if scores:
                strategy_prior_note = (
                    "Historical strategy scores (action: confidence): "
                    + ", ".join(f"{s.strategy_key}={s.confidence:.2f}" for s in scores)
                )
                thinking_steps.append(f"   - Found {len(scores)} historical strategy scores")
        except Exception as sc_exc:
            logger.debug("StrategyScore query failed: %s", sc_exc)
            thinking_steps.append(f"   - StrategyScore query failed")

        # Task 7: episode prior summary for prompt
        if episode_priors:
            ep_strs = [
                f"'{e['action_taken']}' success={e['success']} water_delta={e['water_delta_pct']}%"
                for e in episode_priors[:3]
            ]
            episode_note = f"\nSimilar past episodes: {'; '.join(ep_strs)}."
            thinking_steps.append(f"   - Episode priors: {len(episode_priors)} similar episodes")

        # Operational RAG: HVAC Manuals
        thinking_steps.append(f"⚙️ STEP 4: Retrieving operational knowledge (HVAC manuals)")
        try:
            from app.mcp.tools import retrieve_hvac_manual
            manuals = retrieve_hvac_manual(db, f"How to resolve {risks.get('primary_risk', 'high temps')}?", k=1)
            if manuals:
                manual_note = f"\nRelevant HVAC SOP '{manuals[0]['title']}': {manuals[0]['content']}"
                thinking_steps.append(f"   - Found manual: {manuals[0]['title']}")
        except Exception as e:
            logger.debug("Operational RAG skipped: %s", e)
            thinking_steps.append(f"   - Manual retrieval failed")

    if use_memory:
        system_prompt = (
            "You are the Cooling & Power Optimizer Agent.\n"
            "Propose TWO candidate strategies and select the best one.\n"
            "Respond ONLY with a valid JSON object containing:\n"
            '  "recommendation": string (chosen strategy)\n'
            '  "confidence": float between 0 and 1\n'
            '  "expected_water_saving": float\n'
            '  "rationale": string\n'
            '  "reasoning": detailed step-by-step analysis of your decision\n'
            '  "alternative": string (the other candidate strategy you rejected)\n'
        )
    else:
        system_prompt = (
            "You are a generic data-centre cooling advisor with NO access to historical episodes or memory.\n"
            "Use only the current telemetry and conservative static safety margins.\n"
            "Respond ONLY with a valid JSON object containing:\n"
            '  "recommendation": string (generic conservative strategy)\n'
            '  "confidence": float between 0 and 1 (typically 0.55-0.72 without historical proof)\n'
            '  "expected_water_saving": float (modest estimate, typically 1-5)\n'
            '  "rationale": string (must state no historical context was available)\n'
            '  "reasoning": detailed step-by-step analysis of your decision\n'
            '  "alternative": string (another generic fallback you rejected)\n'
        )

    user_prompt = (
        f"Risk Level: {risks.get('risk_level')}, Primary Risk: {risks.get('primary_risk')}.\n"
        f"Current Cooling: {water.get('cooling_load_kw')}kW, WUE Factor: {water.get('wue_factor', 0.4)}.\n"
        + (f"{strategy_prior_note}\n" if strategy_prior_note else "")
        + episode_note
        + manual_note
        + "\n\nPlease provide detailed step-by-step reasoning for your optimization strategy."
    )

    rl.log_step(run_id, "OptimizerAgent", "input", {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "risk_level": risks.get('risk_level'),
        "primary_risk": risks.get('primary_risk'),
        "note": "Computing optimal cooling strategy"
    })

    thinking_steps.append(f"⚙️ STEP 5: Invoking LLM for strategy optimization")
    thinking_steps.append(f"   - Context: {'Memory-enabled' if use_memory else 'Telemetry-only'}")
    thinking_steps.append(f"   - Strategy priors: {strategy_prior_note[:100] if strategy_prior_note else 'None'}")
    
    rl.log_step(run_id, "OptimizerAgent", "thinking", {"steps": thinking_steps, "phase": "llm_invocation"})

    llm_confidence = 0.88
    alternative = None
    try:
        res = generate_reasoning_with_fallback(run_id, "OptimizerAgent", system_prompt, user_prompt)
        parsed = res.get("parsed_json", {})
        llm_confidence = float(parsed.get("confidence", 0.88))
        alternative = parsed.get("alternative")
        
        thinking_steps.append(f"⚙️ STEP 6: Processing LLM optimization response")
        thinking_steps.append(f"   - Provider: {res.get('provider')}")
        thinking_steps.append(f"   - Chosen Strategy: {parsed.get('recommendation', 'N/A')[:80]}")
        thinking_steps.append(f"   - Alternative: {alternative[:80] if alternative else 'None'}")
        thinking_steps.append(f"   - Expected Savings: {parsed.get('expected_water_saving', 0)}L/hr")
        
        optimization = {
            "recommendation": parsed.get("recommendation", "Increase liquid cooling flow by 12% to maintain thermal equilibrium."),
            "confidence": llm_confidence,
            "expected_water_saving": float(parsed.get("expected_water_saving", 5.2)),
            "rationale": parsed.get("rationale", "Standard cooling optimization based on current metrics"),
            "reasoning": parsed.get("reasoning", "Analyzing thermal load and risk factors to determine optimal cooling strategy"),
            "alternative": alternative,
            "llm_provider": res.get("provider"),
            "llm_raw_response": res.get("raw_text", ""),
            "thinking": "\n".join(thinking_steps),
        }
    except Exception as exc:
        logger.error("OptimizerAgent LLM failed (%s), no fallback available - check Ollama/Groq configuration", exc)
        thinking_steps.append(f"❌ LLM FAILED: {exc}")
        raise RuntimeError(f"OptimizerAgent LLM reasoning failed: {exc}. Please check Ollama and Groq configuration.")

    # Task 6: 60/40 blend with StrategyScore (memory-enabled runs only)
    if use_memory:
        thinking_steps.append(f"⚙️ STEP 7: Blending LLM confidence with historical StrategyScore")
        try:
            from app.models_ext import StrategyScore
            key = optimization["recommendation"][:80]  # truncate for key
            score = db.get(StrategyScore, key)
            if score and (score.success_count + score.failure_count) >= 3:
                blended = round(0.6 * optimization["confidence"] + 0.4 * score.confidence, 3)
                optimization["confidence"] = blended
                optimization["rationale"] += f" [StrategyScore blended: {blended:.2f}]"
                thinking_steps.append(f"   - Historical confidence: {score.confidence:.2f}")
                thinking_steps.append(f"   - Blended confidence: {blended:.2f}")
        except Exception as blend_exc:
            logger.debug("StrategyScore blending skipped: %s", blend_exc)
            thinking_steps.append(f"   - Blending skipped: {blend_exc}")

    # Task 5: log rejected alternative
    alternatives_rejected = [alternative] if alternative else []
    thinking_steps.append(f"⚙️ STEP 8: Final optimization plan")
    thinking_steps.append(f"   - Final confidence: {optimization['confidence']:.2f}")
    thinking_steps.append(f"   - Rejected alternatives: {len(alternatives_rejected)}")
    
    rl.log_step(
        run_id, "OptimizerAgent", "reasoning",
        {**optimization, "alternative": alternative},
        alternatives_rejected=alternatives_rejected,
    )

    state["optimization_plan"] = optimization
    state["agent_trace"].append({"agent": "OptimizerAgent", "plan": optimization, "alternative": alternative, "thinking": "\n".join(thinking_steps)})
    return state


def action_node(state: AgentState) -> AgentState:
    """Node 4: Action Agent — Validates cluster health & safety guardrails, executes state mutation & memory storage via MCP."""
    run_id = state["run_id"]
    db = state["db"]
    opt = state["optimization_plan"]
    twin = state["twin_dict"]

    # Agent thinking process
    thinking_steps = [
        f"🤖 STEP 1: Preparing to execute recommended action",
        f"   - Recommendation: {opt['recommendation'][:80]}",
        f"   - Confidence: {opt['confidence']:.2f}",
        f"   - Expected Savings: {opt['expected_water_saving']}L/hr",
        f"🤖 STEP 2: Checking cluster health and safety guardrails"
    ]
    
    rl.log_step(run_id, "ActionAgent", "thinking", {"steps": thinking_steps, "phase": "pre_execution"})

    rl.log_step(run_id, "ActionAgent", "input", {
        "recommendation": opt["recommendation"],
        "confidence": opt["confidence"],
        "note": "Validating cluster health and safety guardrails"
    })

    # Check CockroachDB cluster health via ccloud MCP tool
    thinking_steps.append(f"🤖 STEP 3: Invoking CockroachDB cluster health check tool")
    cluster_status = ccloud_cluster_health()
    thinking_steps.append(f"   - Cluster Status: {cluster_status.get('status', 'unknown')}")
    
    rl.log_step(run_id, "ActionAgent", "tool_call", {
        "tool": "ccloud_cluster_health",
        "cluster_status": cluster_status
    })

    # Validate with Guardrail Critic
    thinking_steps.append(f"🤖 STEP 4: Running Guardrail Critic safety validation")
    critic = GuardrailCriticAgent()
    draft = {
        "recommendation": opt["recommendation"],
        "confidence": opt["confidence"],
        "cited_memory_ids": [m.get("id") for m in state["retrieved_memories"] if m.get("id")],
        "rationale": opt["rationale"],
    }
    critic_res = critic.run({"twin_state": twin, "open_incidents": state["open_incidents"]}, draft)
    
    thinking_steps.append(f"   - Guardrail Passed: {critic_res.get('passed', True)}")
    thinking_steps.append(f"   - Flags: {critic_res.get('flags', [])}")
    thinking_steps.append(f"   - Adjusted Confidence: {critic_res.get('confidence_adjusted', opt['confidence']):.2f}")
    
    rl.log_step(run_id, "GuardrailCritic", "guardrail", {
        "passed": critic_res.get("passed", True),
        "flags": critic_res.get("flags", []),
        "confidence_adjusted": critic_res.get("confidence_adjusted", opt["confidence"])
    })

    passed = critic_res.get("passed", True)
    final_conf = opt["confidence"] if passed else critic_res.get("confidence_adjusted", 0.5)

    # Simulated Closed-Loop Actuation
    actuation_result = None
    if passed:
        thinking_steps.append(f"🤖 STEP 5: Executing closed-loop actuation")
        import requests
        try:
            rec = opt["recommendation"].lower()
            if "migrate" in rec or "workload" in rec:
                thinking_steps.append(f"   - Actuation Type: Workload Migration")
                act_resp = requests.post("http://127.0.0.1:8000/api/v1/actuation/workload/migrate", json={
                    "source_rack_id": twin.get("rack_id", "RACK-1"),
                    "target_rack_id": "RACK-2",
                    "workload_type": "LLM Inference"
                }, timeout=5)
                actuation_result = act_resp.json()
            else:
                thinking_steps.append(f"   - Actuation Type: HVAC Throttle")
                act_resp = requests.post("http://127.0.0.1:8000/api/v1/actuation/hvac/throttle", json={
                    "rack_id": twin.get("rack_id", "RACK-1"),
                    "target_fan_speed_rpm": 2800.0,
                    "target_chiller_setpoint_c": 19.5
                }, timeout=5)
                actuation_result = act_resp.json()
            logger.info("Closed-Loop Actuation executed: %s", actuation_result)
            thinking_steps.append(f"   - Actuation Result: {actuation_result}")
            rl.log_step(run_id, "ActionAgent", "tool_call", {
                "tool": "actuation_api",
                "actuation_type": "workload_migrate" if "migrate" in rec or "workload" in rec else "hvac_throttle",
                "actuation_result": actuation_result
            })
        except Exception as act_exc:
            logger.error("Closed-Loop Actuation failed: %s", act_exc)
            actuation_result = {"error": str(act_exc)}
            thinking_steps.append(f"   - Actuation Failed: {act_exc}")
            rl.log_step(run_id, "ActionAgent", "error", {
                "error": "Actuation failed",
                "details": str(act_exc)
            })
    else:
        thinking_steps.append(f"🤖 STEP 5: Actuation SKIPPED (guardrail failed)")

    # Persist agent memory via MCP tool (memory-enabled runs only)
    stored_mem = {}
    if db and state.get("use_memory", True):
        logger.info(f"🧠 MEMORY STORAGE ATTEMPT: use_memory={state.get('use_memory', True)}, db_exists={db is not None}")
        thinking_steps.append(f"🤖 STEP 6: Storing decision to agent memory")
        try:
            summary = f"Action: {opt['recommendation']} | Expected Saving: {opt['expected_water_saving']}L/hr | Confidence: {final_conf}"
            device_id = twin.get("device_id", "rack-01-primary")  # Get device_id from twin_dict
            logger.info(f"🧠 MEMORY STORAGE: Calling store_agent_memory with device_id={device_id}")
            stored_mem = store_agent_memory(db, memory_type="recommendation", source_id=run_id, summary=summary, device_id=device_id)
            logger.info(f"✅ MEMORY STORAGE SUCCESS: {stored_mem}")
            thinking_steps.append(f"   - Memory ID: {stored_mem.get('id', 'N/A')}")
            thinking_steps.append(f"   - Memory Type: recommendation")
            rl.log_step(run_id, "ActionAgent", "tool_call", {
                "tool": "store_agent_memory",
                "memory_type": "recommendation",
                "stored_memory": stored_mem
            })
        except Exception as exc:
            logger.error(f"❌ MEMORY STORAGE FAILED: {exc}")
            logger.warning("ActionAgent memory persistence failed: %s", exc)
            thinking_steps.append(f"   - Memory Storage Failed: {exc}")
            rl.log_step(run_id, "ActionAgent", "error", {
                "error": "Memory persistence failed",
                "details": str(exc)
            })
            try:
                db.rollback()
            except Exception:
                pass
    else:
        logger.warning(f"⚠️ MEMORY STORAGE SKIPPED: use_memory={state.get('use_memory', True)}, db_exists={db is not None}")
        thinking_steps.append(f"   - Memory Storage Skipped: use_memory={state.get('use_memory', True)}")

    thinking_steps.append(f"🤖 STEP 7: Final action result")
    thinking_steps.append(f"   - Guardrail Passed: {passed}")
    thinking_steps.append(f"   - Final Confidence: {final_conf:.2f}")
    thinking_steps.append(f"   - Memory Stored: {bool(stored_mem)}")

    action_result = {
        "cluster_health": cluster_status,
        "guardrail_passed": passed,
        "final_confidence": final_conf,
        "stored_memory": stored_mem,
        "actuation_result": actuation_result,
        "recommendation": opt["recommendation"],
        "expected_water_saving": opt["expected_water_saving"],
        "confidence_at_decision": final_conf,
        "thinking": "\n".join(thinking_steps),
    }

    state["action_result"] = action_result
    state["agent_trace"].append({"agent": "ActionAgent", "result": action_result, "thinking": "\n".join(thinking_steps)})
    rl.log_step(run_id, "ActionAgent", "reasoning", action_result)
    return state


def reflect_node(state: AgentState) -> AgentState:
    """Node 5 (Task 6): Reflect Agent — Creates an initial Episode row capturing the
    decision context immediately after action execution. Outcome fields (water_delta_pct,
    temp_delta_c, success, reward) are left NULL and resolved asynchronously by
    outcome_watcher.resolve_pending_episodes() ~15 minutes later."""
    if not state.get("use_memory", True):
        return state

    run_id = state["run_id"]
    db = state["db"]
    opt = state["optimization_plan"]
    act = state["action_result"]
    twin = state["twin_dict"]
    water = state["water_out"]

    # Agent thinking process
    thinking_steps = [
        f"🔄 STEP 1: Creating episode record for reinforcement learning",
        f"   - Run ID: {run_id}",
        f"   - Action Taken: {opt.get('recommendation', '')[:80]}",
        f"   - Expected Water Saving: {opt.get('expected_water_saving')}L/hr",
        f"   - Final Confidence: {act.get('final_confidence', opt.get('confidence', 0.5)):.2f}",
        f"🔄 STEP 2: Capturing system state snapshot",
        f"   - Telemetry: {twin.get('utilisation_pct')}% utilisation",
        f"   - Water Usage: {water.get('water_l_per_hr')}L/hr",
        f"   - Cooling Load: {water.get('cooling_load_kw')}kW"
    ]
    
    rl.log_step(run_id, "ReflectAgent", "thinking", {"steps": thinking_steps, "phase": "episode_creation"})

    try:
        from app.models_ext import Episode
        from app import models
        import uuid as _uuid

        thinking_steps.append(f"🔄 STEP 3: Validating recommendation linkage")
        rec_id = act.get("stored_memory", {}).get("id")
        if rec_id and db:
            # Validate rec_id actually exists in recommendations table to avoid FK violation
            if not db.get(models.Recommendation, rec_id):
                rec_id = None
                thinking_steps.append(f"   - Recommendation validation failed - using None")
            else:
                thinking_steps.append(f"   - Recommendation ID: {rec_id}")

        thinking_steps.append(f"🔄 STEP 4: Creating episode record")
        ep = Episode(
            episode_id=str(_uuid.uuid4()),
            run_id=run_id,
            device_id=twin.get("device_id", "rack-01-primary"),  # Add device_id from twin_dict
            rack_id=twin.get("rack_id"),
            recommendation_id=rec_id,
            telemetry_snapshot={
                k: twin.get(k)
                for k in ["cpu_pct", "gpu_pct", "gpu_temp", "ram_pct", "utilisation_pct"]
                if twin.get(k) is not None
            },
            water_snapshot={
                k: water.get(k)
                for k in ["water_l_per_hr", "cooling_load_kw", "wue_factor", "pue", "thermal_load_kw", "utilisation_pct"]
                if water.get(k) is not None
            },
            action_taken=opt.get("recommendation", "")[:200],
            action_params={"expected_water_saving": opt.get("expected_water_saving")},
            confidence_at_decision=act.get("final_confidence", opt.get("confidence", 0.5)),
        )
        
        thinking_steps.append(f"   - Episode ID: {ep.episode_id}")
        thinking_steps.append(f"   - Device ID: {ep.device_id}")
        thinking_steps.append(f"   - Rack ID: {ep.rack_id}")
        
        if db:
            db.add(ep)
            db.commit()
            thinking_steps.append(f"   - Episode stored successfully")
        
        thinking_steps.append(f"🔄 STEP 5: Episode created - outcome to be resolved asynchronously")
        
        rl.log_step(run_id, "ReflectAgent", "reasoning", {
            "episode_id": ep.episode_id,
            "note": "Episode created; outcome pending outcome_watcher resolution.",
            "thinking": "\n".join(thinking_steps),
        })
        state["agent_trace"].append({"agent": "ReflectAgent", "episode_id": ep.episode_id, "thinking": "\n".join(thinking_steps)})
    except Exception as exc:
        if db:
            db.rollback()
        thinking_steps.append(f"❌ Episode creation failed: {exc}")
        logger.warning("ReflectAgent episode creation failed: %s", exc)
        rl.log_step(run_id, "ReflectAgent", "error", {
            "error": "Episode creation failed",
            "details": str(exc),
            "thinking": "\n".join(thinking_steps)
        })

    return state


def explainer_node(state: AgentState) -> AgentState:
    """Node 5: Explainer Agent — Assembles comprehensive operator-facing response and decision audit."""
    run_id = state["run_id"]
    opt = state["optimization_plan"]
    act = state["action_result"]
    memories = state["retrieved_memories"]

    # Agent thinking process
    thinking_steps = [
        f"📝 STEP 1: Assembling comprehensive operator-facing response",
        f"   - Final Recommendation: {opt['recommendation'][:80]}",
        f"   - Final Confidence: {act['final_confidence']:.2f}",
        f"   - Guardrail Status: {'PASSED' if act['guardrail_passed'] else 'ADJUSTED'}",
        f"📝 STEP 2: Compiling decision audit and citations",
        f"   - Cited Memories: {len([m['id'] for m in memories if 'id' in m])}",
        f"   - Episode Priors: {len(state.get('episode_priors', []))}",
        f"   - Memory System: {'Enabled' if state.get('use_memory', True) else 'Disabled'}"
    ]
    
    rl.log_step(run_id, "ExplainerAgent", "thinking", {"steps": thinking_steps, "phase": "explanation_assembly"})

    cited_ids = [m["id"] for m in memories if "id" in m]

    explanation_text = (
        f"Recommendation: {opt['recommendation']} "
        f"(Confidence: {act['final_confidence']:.2f}, Rationale: {opt['rationale']}). "
        f"Validated by Guardrail Critic ({'PASSED' if act['guardrail_passed'] else 'ADJUSTED'})."
    )

    thinking_steps.append(f"📝 STEP 3: Final explanation assembled")
    thinking_steps.append(f"   - Text: {explanation_text[:100]}...")

    use_memory = state.get("use_memory", True)
    final_output = {
        "run_id": run_id,
        "recommendation": opt["recommendation"],
        "recommendation_full": explanation_text,
        "confidence": act["final_confidence"],
        "agent_name": "langgraph_multi_agent" if use_memory else "baseline_no_memory",
        "cited_memory_ids": cited_ids if use_memory else [],
        "cited_episodes_count": len(state.get("episode_priors", [])) if use_memory else 0,
        "rationale": opt["rationale"] if not use_memory else f"LangGraph State Machine (Monitor->Predictor->Optimizer->Action->Explainer) | {opt['rationale']}",
        "agent_trace": state["agent_trace"],
        "expected_water_saving": opt.get("expected_water_saving", 0.0),
        "use_memory": use_memory,
        "thinking": "\n".join(thinking_steps),
    }

    state["agent_trace"].append({"agent": "ExplainerAgent", "explanation": explanation_text, "thinking": "\n".join(thinking_steps)})
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

    def run(
        self,
        db: Session,
        twin_state_obj,
        water_out: dict,
        open_incidents: int,
        *,
        use_memory: bool = True,
    ) -> Dict[str, Any]:
        run_id = rl.new_run_id()
        
        # Handle both dict and object inputs
        if isinstance(twin_state_obj, dict):
            twin_dict = twin_state_obj
        else:
            twin_dict = twin_state_obj.model_dump()

        initial_state: AgentState = {
            "run_id": run_id,
            "db": db,
            "twin_dict": twin_dict,
            "water_out": water_out,
            "open_incidents": open_incidents,
            "use_memory": use_memory,
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
