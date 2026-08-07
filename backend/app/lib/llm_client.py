"""
LLM Client Manager for RackPulse.
Optimized for local Ollama (Qwen) calls with fallback to Groq and connection pooling.
"""

import json
import logging
import re
import time
from typing import Dict, List, Optional, Any

import httpx

from app.config import settings
from app.observability import reasoning_logger as rl

logger = logging.getLogger("aquamind.llm_client")

# Shared connection pool for high-performance HTTP execution
_http_client: Optional[httpx.Client] = None


def get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(
            timeout=httpx.Timeout(120.0, connect=10.0),  # 2 minutes total, 10s connect - better for interactive use
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _http_client


def extract_json_from_llm_response(raw_text: str) -> Dict[str, Any]:
    """Extracts JSON structure from markdown wrappers or raw LLM output text."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {raw_text[:300]}")
    return json.loads(match.group(0))


def call_ollama_qwen(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Invokes local Ollama with Qwen model using optimized HTTP connection pool."""
    model_name = model or settings.OLLAMA_MODEL
    timeout = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS
    client = get_http_client()

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,  # Lower temperature for more accurate/consistent responses
            "num_predict": 2048,  # Increased context window for better reasoning
            "top_p": 0.9,  # Nucleus sampling for better quality
            "top_k": 40,  # Top-k sampling for focused responses
        },
    }

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    response = client.post(url, json=payload, timeout=float(timeout))
    response.raise_for_status()

    data = response.json()
    content = data.get("message", {}).get("content", "")
    if not content:
        raise ValueError(f"Ollama returned empty response: {data}")

    return {
        "raw_text": content,
        "parsed_json": extract_json_from_llm_response(content),
        "model": model_name,
        "provider": "ollama_qwen",
    }


def call_groq_fallback(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Invokes Groq API as high-reliability fallback when local Ollama is unavailable."""
    if not settings.GROQ_ENABLED or not settings.GROQ_API_KEY:
        raise RuntimeError("Groq fallback is disabled or GROQ_API_KEY is missing.")

    model_name = model or settings.GROQ_MODEL
    timeout = timeout_seconds or settings.GROQ_TIMEOUT_SECONDS
    client = get_http_client()

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,  # Lower temperature for consistency
        "response_format": {"type": "json_object"},
        "max_tokens": 2048,  # Increased context window
        "top_p": 0.9,  # Better quality sampling
    }

    response = client.post(url, headers=headers, json=payload, timeout=float(timeout))
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return {
        "raw_text": content,
        "parsed_json": extract_json_from_llm_response(content),
        "model": model_name,
        "provider": "groq",
    }


def generate_reasoning_with_fallback(
    run_id: str,
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    preferred_ollama_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Primary strategy: Ollama (Qwen).
    Fallback strategy: Groq.
    Third safety net: Exception raised to caller.
    
    Optimized for accuracy with better error handling and retry logic.
    """
    if settings.OLLAMA_ENABLED:
        try:
            rl.log_step(
                run_id,
                agent_name,
                "reasoning",
                {
                    "note": "Calling primary LLM (Ollama Qwen)",
                    "model": preferred_ollama_model or settings.OLLAMA_MODEL,
                },
            )
            res = call_ollama_qwen(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=preferred_ollama_model,
            )
            rl.log_step(
                run_id,
                agent_name,
                "reasoning",
                {"note": "Ollama Qwen call succeeded", "provider": res["provider"]},
            )
            return res
        except Exception as exc:
            logger.warning(
                "Ollama Qwen call failed for run_id=%s agent=%s: %s. Falling back to Groq.",
                run_id,
                agent_name,
                exc,
            )
            rl.log_error(run_id, agent_name, f"Ollama Qwen failed: {exc}. Attempting Groq fallback.")

    if settings.GROQ_ENABLED and settings.GROQ_API_KEY:
        try:
            rl.log_step(
                run_id,
                agent_name,
                "reasoning",
                {"note": "Calling secondary LLM (Groq)", "model": settings.GROQ_MODEL},
            )
            res = call_groq_fallback(system_prompt=system_prompt, user_prompt=user_prompt)
            rl.log_step(
                run_id,
                agent_name,
                "reasoning",
                {"note": "Groq fallback call succeeded", "provider": res["provider"]},
            )
            return res
        except Exception as exc:
            logger.error(
                "Groq fallback call failed for run_id=%s agent=%s: %s.",
                run_id,
                agent_name,
                exc,
            )
            rl.log_error(run_id, agent_name, f"Groq fallback failed: {exc}")

    raise RuntimeError("All LLM reasoning providers (Ollama Qwen & Groq) failed.")
