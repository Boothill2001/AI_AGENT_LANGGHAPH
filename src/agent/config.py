"""Configuration: LLM credentials and agent guardrails."""

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _clean_key(raw: str) -> str:
    """Extract the bare `sk-...` token, tolerating quotes/comments in .env values."""
    match = re.search(r"sk-[A-Za-z0-9]+", raw)
    return match.group(0) if match else raw.strip()


DEEPSEEK_API_KEY = _clean_key(
    os.getenv("DEEPSEEK_KEY")
    or os.getenv("deepseek_key")
    or os.getenv("DEEPSEEK_API_KEY")
    or ""
)
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# MCP server launch command (stdio transport)
MCP_SERVER = {
    "research": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "mcp_server" / "server.py")],
        "transport": "stdio",
    }
}

# Tools that must NOT run without explicit human approval
SENSITIVE_TOOLS = {"save_report"}

# Guardrail: hard cap on planner<->tools loops per user turn
MAX_AGENT_ITERATIONS = 8
