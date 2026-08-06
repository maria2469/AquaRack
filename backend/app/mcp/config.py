"""
Configuration for CockroachDB Managed MCP Server.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    COCKROACH_MCP_ENDPOINT: str = os.getenv("COCKROACH_MCP_ENDPOINT", "")
    COCKROACH_MCP_API_KEY: str = os.getenv("COCKROACH_MCP_API_KEY", "")
    MCP_ENABLED: bool = True
    MCP_TIMEOUT_SECONDS: float = 10.0
    


mcp_config = MCPConfig()
