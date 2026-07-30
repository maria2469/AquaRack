"""
AWS Secrets Manager client wrapper (Enterprise Security).

Safely fetches sensitive secrets (database URLs, API tokens, encryption keys)
from AWS Secrets Manager when SECRETS_MANAGER_ENABLED=true and boto3 +
credentials are available.

Falls back cleanly to local environment variables / .env file if AWS credentials,
network connection, or secrets are unavailable — preserving zero mandatory cloud dependency.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger("aquamind.secrets_manager")

_secrets_client = None
_secrets_unavailable = False


def _get_secrets_client():
    """Lazily creates and caches a boto3 Secrets Manager client."""
    global _secrets_client, _secrets_unavailable
    if _secrets_client is not None:
        return _secrets_client
    if _secrets_unavailable:
        return None
    try:
        import boto3

        _secrets_client = boto3.client("secretsmanager", region_name=settings.AWS_REGION)
        return _secrets_client
    except Exception as e:
        logger.warning(f"boto3 Secrets Manager client unavailable: {e}")
        _secrets_unavailable = True
        return None


def get_secret(secret_name: Optional[str] = None, region_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves a secret from AWS Secrets Manager and parses it as a JSON dict.
    Returns None if SECRETS_MANAGER_ENABLED=false or if retrieval fails, allowing
    the caller to fall back to .env / Pydantic settings.
    """
    if not settings.SECRETS_MANAGER_ENABLED:
        return None

    client = _get_secrets_client()
    if client is None:
        return None

    target_secret = secret_name or settings.SECRETS_MANAGER_SECRET_NAME
    try:
        response = client.get_secret_value(SecretId=target_secret)
        if "SecretString" in response:
            try:
                return json.loads(response["SecretString"])
            except json.JSONDecodeError:
                return {"secret": response["SecretString"]}
    except Exception as exc:
        logger.warning(f"Failed to retrieve secret '{target_secret}' from AWS Secrets Manager: {exc}")
    return None
