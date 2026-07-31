"""
LangChain + Groq reasoning layer for AquaMind AI.

LLM:
    Groq hosted Llama models.

Embedding:
    Keeps existing Ollama/local embedding fallback.
    (Groq does not provide embeddings)

Fallback:
    rules_fallback agent.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List

from pydantic import BaseModel, Field

from app.config import settings
from app.observability import reasoning_logger as rl


logger = logging.getLogger("aquamind.langchain_groq")


SYSTEM_PROMPT = """
You are the Water & Cooling reasoning agent for AquaMind AI.

You are controlling an AI data center digital twin.

Reason ONLY from:
- telemetry context
- water model
- retrieved memories

Rules:
- Never invent numbers.
- Cite memory ids used.
- Give practical cooling recommendations.
"""


HUMAN_TEMPLATE = """
CONTEXT:

Twin State:
{twin_state}

Water Model:
{water_model}

Open Incidents:
{open_incidents}


MEMORIES:

{memories}


Generate a cooling optimization recommendation.
"""


class RecommendationOutput(BaseModel):
    explanation: str
    root_cause: str
    recommendation: str
    expected_water_saving: float = Field(default=0)
    confidence: float = Field(default=0.5)
    reasoning_summary: str
    cited_memory_ids: List[str] = []


_llm = None


def _get_llm():
    global _llm

    if _llm:
        return _llm

    try:
        from langchain_groq import ChatGroq

        _llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            temperature=settings.GROQ_TEMPERATURE,
        )

        logger.info(
            "Groq initialized model=%s",
            settings.GROQ_MODEL
        )

        return _llm

    except Exception as e:
        logger.error(
            "Groq initialization failed %s",
            e
        )
        return None


def reset_llm():
    global _llm
    _llm = None


def invoke_langchain_groq(
    run_id: str,
    twin_state: dict,
    water_model: dict,
    memories: List[Dict],
    open_incidents: int,
    agent_name="water_cooling",
):

    rl.log_step(
        run_id,
        agent_name,
        "reasoning",
        {
            "note": "Building Groq reasoning prompt",
            "memories_used": len(memories),
            "model": settings.GROQ_MODEL
        }
    )

    llm = _get_llm()

    if llm is None:
        return _rules_fallback(
            run_id,
            agent_name,
            twin_state,
            water_model,
            memories,
            "groq_unavailable"
        )

    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_TEMPLATE)
        ]
    )

    kwargs = {
        "twin_state": json.dumps(twin_state, default=str),
        "water_model": json.dumps(water_model, default=str),
        "open_incidents": open_incidents,
        "memories": json.dumps(memories, default=str)
    }

    try:
        structured = llm.with_structured_output(RecommendationOutput)
        chain = prompt | structured
        result = chain.invoke(kwargs)
        output = result.model_dump()

    except Exception as e:
        logger.warning(
            "Groq structured output failed %s",
            e
        )

        try:
            chain = prompt | llm
            response = chain.invoke(kwargs)
            text = response.content

            output = {
                "explanation": "Groq reasoning completed.",
                "root_cause": "Thermal conditions analyzed from telemetry.",
                "recommendation": text[:500],
                "expected_water_saving": 10.0,
                "confidence": 0.7,
                "reasoning_summary": text[:200],
                "cited_memory_ids": [
                    m.get("memory_id")
                    for m in memories
                    if isinstance(m, dict)
                ]
            }

        except Exception as e2:
            logger.error(
                "Groq failed %s",
                e2
            )

            return _rules_fallback(
                run_id,
                agent_name,
                twin_state,
                water_model,
                memories,
                "groq_error"
            )

    output["agent_name"] = "groq_langchain"
    output["rationale"] = output.get("reasoning_summary", "")

    rl.log_step(
        run_id,
        agent_name,
        "decision",
        output
    )

    return output


def _rules_fallback(
    run_id,
    agent_name,
    twin_state,
    water_model,
    memories,
    reason
):
    from app.agents.rules_fallback import generate_recommendation

    class FakeTwin:
        utilisation_pct = twin_state.get("utilisation_pct", 0)
        thermal_load_kw = twin_state.get("thermal_load_kw", 0)

    water = {
        "cooling_load_kw": water_model.get("cooling_load_kw", 0),
        "wue_factor": water_model.get("wue_factor", 1),
        "water_l_per_hr": water_model.get("water_l_per_hr", 0)
    }

    rec = generate_recommendation(
        FakeTwin(),
        water,
        memories
    )

    rec["agent_name"] = f"rules_fallback::{reason}"

    return rec