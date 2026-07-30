"""
LangChain + Amazon Bedrock reasoning layer (SDD Section 16 / Tech Stack:
"Amazon Bedrock reasoning" via "LangChain").

Replaces the earlier raw-boto3 bedrock_client.py call with a proper
LangChain chain:
  ChatBedrockConverse (LLM)  ->  structured output (RecommendationOutput)
  BedrockEmbeddings          ->  used by the Memory Engine for real
                                  Titan embeddings when BEDROCK_ENABLED.

Every step is pushed to the real-time reasoning log (shared/observability)
as it happens, so `tail -f aquamind_reasoning.log` (or the SSE endpoint)
shows the agent's live thinking: what context it was given, that it's
calling Bedrock, and what it decided — not just the final answer.

Falls back to the deterministic rules_fallback agent on ANY failure
(missing credentials, network, throttling, parsing) — SDD FR-1.11,
"zero mandatory cloud dependency" is preserved.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.observability import reasoning_logger as rl

SYSTEM_PROMPT = (
    "You are the Water & Cooling reasoning agent for AquaMind AI, an AI "
    "data-centre digital twin. Reason ONLY from the provided CONTEXT and "
    "MEMORIES. Cite memory ids you actually use in cited_memory_ids. Do "
    "not invent numeric values that are not present in CONTEXT or MEMORIES."
)

HUMAN_TEMPLATE = (
    "CONTEXT:\n"
    "twin_state: {twin_state}\n"
    "water_model: {water_model}\n"
    "open_incidents: {open_incidents}\n\n"
    "MEMORIES (top-K retrieved via RAG):\n{memories}\n\n"
    "Produce a cooling/water-management recommendation grounded in the "
    "above."
)


class RecommendationOutput(BaseModel):
    """Enterprise Structured Output for Amazon Bedrock Reasoning."""

    explanation: str = Field(description="Operational summary of current telemetry and water impact.")
    root_cause: str = Field(description="Diagnosed root cause for thermal/water inefficiency.")
    recommendation: str = Field(description="Actionable water optimization recommendation.")
    expected_water_saving: float = Field(description="Estimated water saving percentage (e.g. 17.8).")
    confidence: float = Field(description="Confidence score in [0.0, 1.0].", ge=0.0, le=1.0)
    reasoning_summary: str = Field(description="Short reasoning trace justifying the decision.")
    cited_memory_ids: List[str] = Field(default_factory=list, description="Historical memory IDs referenced.")


_llm = None  # lazy singleton, only constructed if BEDROCK_ENABLED


def _get_llm():
    """Lazily build the LangChain ChatBedrockConverse client (Section 16)."""
    global _llm
    if _llm is None:
        from langchain_aws import ChatBedrockConverse

        _llm = ChatBedrockConverse(
            model=settings.BEDROCK_TEXT_MODEL_ID,
            region_name=settings.AWS_REGION,
            temperature=0.2,
            max_tokens=600,
        )
    return _llm


def invoke_langchain(
    run_id: str,
    twin_state: dict,
    water_model: dict,
    memories: List[Dict],
    open_incidents: int,
    agent_name: str = "water_cooling",
) -> Dict:
    """
    Runs the LangChain prompt -> ChatBedrockConverse -> structured-output chain.
    """
    from langchain_core.prompts import ChatPromptTemplate

    rl.log_step(
        run_id, agent_name, "reasoning",
        {"note": "Building LangChain prompt from CONTEXT + retrieved MEMORIES via CockroachDB MCP",
         "memories_used": len(memories)},
    )

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", HUMAN_TEMPLATE)]
    )

    llm = _get_llm()
    structured_llm = llm.with_structured_output(RecommendationOutput)
    chain = prompt | structured_llm

    rl.log_step(
        run_id, agent_name, "tool_call",
        {"note": "Invoking Amazon Bedrock via LangChain ChatBedrockConverse",
         "model_id": settings.BEDROCK_TEXT_MODEL_ID, "region": settings.AWS_REGION},
    )

    result: RecommendationOutput = chain.invoke(
        {
            "twin_state": json.dumps(twin_state, default=str),
            "water_model": json.dumps(water_model, default=str),
            "open_incidents": open_incidents,
            "memories": json.dumps(memories, default=str),
        }
    )

    out = result.model_dump()
    out["agent_name"] = f"bedrock_langchain::{agent_name}"
    out["rationale"] = out.get("reasoning_summary", out.get("explanation", ""))

    rl.log_step(
        run_id, agent_name, "reasoning",
        {"note": "Bedrock returned structured recommendation via LangChain", "raw": out},
    )

    return out


def embed_text_langchain(text: str) -> Optional[List[float]]:
    """
    Real Titan embedding via LangChain's BedrockEmbeddings (Section 11.2 / 15.2).
    """
    from langchain_aws import BedrockEmbeddings

    embedder = BedrockEmbeddings(
        model_id=settings.BEDROCK_EMBED_MODEL_ID,
        region_name=settings.AWS_REGION,
    )
    return embedder.embed_query(text)

