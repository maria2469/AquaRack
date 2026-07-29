"""
Amazon Bedrock client for the AI Decision Agent (SDD Section 16).
Only invoked when BEDROCK_ENABLED=true. Any failure falls back to the
rules-based agent (SDD FR-1.11) — see app/agent/orchestrator.py.
"""
import json
from typing import List, Dict

from app.config import settings

PROMPT_TEMPLATE = """SYSTEM: You are the {agent_name} for AquaMind AI, an AI data-centre digital twin. \
Reason only from the provided CONTEXT and MEMORIES. Cite memory ids you use. \
Respond in the required JSON schema. Do not invent numeric values.

CONTEXT: twin_state: {twin_state}; water_model: {water_model}; open_incidents: {open_incidents}

MEMORIES (top-K retrieved): {memories}

OUTPUT SCHEMA (JSON): {{"recommendation": string, "confidence": number(0-1), \
"cited_memory_ids": [string], "rationale": string}}
"""


def build_prompt(twin_state: dict, water_model: dict, memories: List[Dict], open_incidents: int) -> str:
    return PROMPT_TEMPLATE.format(
        agent_name="water_cooling_single_agent",
        twin_state=json.dumps(twin_state),
        water_model=json.dumps(water_model),
        open_incidents=open_incidents,
        memories=json.dumps(memories),
    )


def invoke(twin_state: dict, water_model: dict, memories: List[Dict], open_incidents: int) -> Dict:
    """Raises on any failure — caller is responsible for falling back."""
    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
    prompt = build_prompt(twin_state, water_model, memories, open_incidents)
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }
    )
    resp = client.invoke_model(modelId=settings.BEDROCK_TEXT_MODEL_ID, body=body)
    payload = json.loads(resp["body"].read())
    text = payload["content"][0]["text"]
    parsed = json.loads(text)
    parsed["agent_name"] = "bedrock_single"
    return parsed
