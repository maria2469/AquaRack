"""
Groq-grounded synthesis step for AquaRack memory retrieval.

NEW FILE -- fixes diagnosis issue #6 (synthesis hallucinating recommendations
that don't exist in the retrieved memories) and implements the architectural
improvement in issue #10:

    User Query -> Cockroach VECTOR Search -> Top-K memories -> Groq Llama 3.3 70B
    -> Grounded Answer -> Citations

Uses GROQ_API_KEY_2 from the environment, per your instruction. If you actually
have two Groq keys for a reason (e.g. separate rate-limit pools for ingest vs
query), make sure this really is the one you want the query path to use.
"""
import os
import json
import logging
from typing import Any, Dict, List

from groq import Groq

logger = logging.getLogger("aquamind.groq_synthesis")

GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2")
GROQ_MODEL = "openai/gpt-oss-120b"

if not GROQ_API_KEY_2:
    logger.warning(
        "GROQ_API_KEY_2 is not set. groq_synthesis calls will fail until it is "
        "configured in the environment."
    )

_client = Groq(api_key=GROQ_API_KEY_2) if GROQ_API_KEY_2 else None


SYSTEM_PROMPT = """You are a grounded retrieval-synthesis assistant for a datacenter \
cooling/water-savings system called AquaRack.

You will be given a user query and a set of retrieved memory records (incidents \
and/or recommendations) pulled from a vector database.

STRICT RULES:
- Only state facts, root causes, numbers, and recommendations that appear in the \
provided memory records. Do not invent or infer values that are not present.
- If the retrieved memories do not contain enough information to answer part of \
the query, explicitly say so instead of filling the gap.
- Every recommendation or number you state must be traceable to a specific memory \
ID from the input. Cite memory IDs in a "sources" list.
- If retrieval_method is "fallback_recent", the records are NOT semantic matches \
-- they are just the most recent entries. Say so plainly in your answer; do not \
present them as if they were matched to the query.
- Output valid JSON only, matching the schema given. No prose outside the JSON.
"""

RESPONSE_SCHEMA_HINT = """Respond with ONLY a JSON object of this shape:
{
  "answer": "<grounded natural-language answer, citing memory ids inline like [mem:<id>]>",
  "root_cause": "<string or null, only if directly supported by retrieved memories>",
  "recommendations": ["<string, each drawn from a retrieved recommendation>"],
  "average_predicted_water_saving_pct": <number or null>,
  "sources": ["<memory id>", "..."],
  "caveats": "<string, e.g. note if results came from fallback_recent rather than vector search>"
}
"""


def synthesize_grounded_answer(
    query_text: str,
    incident_result: Dict[str, Any],
    recommendation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Call Groq to produce a grounded answer from retrieved incidents + recommendations.

    incident_result / recommendation_result are the dicts returned by
    retrieve_similar_incidents() / retrieve_previous_recommendations() in
    app/mcp/tools.py (i.e. they include "matches" and "retrieval_method").
    """
    if _client is None:
        raise RuntimeError("GROQ_API_KEY_2 is not configured; cannot run synthesis.")

    payload = {
        "query": query_text,
        "incidents": {
            "retrieval_method": incident_result.get("retrieval_method"),
            "records": incident_result.get("matches", []),
        },
        "recommendations": {
            "retrieval_method": recommendation_result.get("retrieval_method"),
            "records": recommendation_result.get("matches", []),
        },
    }

    logger.info(
        "Groq synthesis: query='%s' incident_method=%s rec_method=%s incidents=%d recs=%d",
        query_text,
        incident_result.get("retrieval_method"),
        recommendation_result.get("retrieval_method"),
        len(incident_result.get("matches", [])),
        len(recommendation_result.get("matches", [])),
    )

    completion = _client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + RESPONSE_SCHEMA_HINT},
            {"role": "user", "content": json.dumps(payload, default=str)},
        ],
    )

    raw = completion.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Groq synthesis returned non-JSON output: %s", raw[:500])
        raise

    return parsed