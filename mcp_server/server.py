"""MCP (Model Context Protocol) server exposing the agent's tools.

Runs as a stdio server — the agent connects to it through an MCP client,
exactly how LLMs are wired to internal tools/APIs in production. Tools:

- knowledge_search  -> proxies the Advanced RAG API (separate project)
- calculator        -> safe AST-based math evaluation (no eval())
- get_current_time  -> current date/time
- save_report       -> writes a markdown report to ./reports/
                       (the agent gates this behind human approval)
"""

import ast
import operator
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research-tools")

RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


# --------------------------------------------------------------------------
@mcp.tool()
def knowledge_search(query: str) -> str:
    """Search the AI/ML knowledge base (RAG pipeline with hybrid search +
    re-ranking) and return a grounded answer with source citations.
    Use this for any question about RAG, retrieval, embeddings, LLMs,
    vector databases, chunking, or AI engineering."""
    try:
        resp = requests.post(
            f"{RAG_API_URL}/ask", json={"question": query}, timeout=90
        )
        resp.raise_for_status()
        data = resp.json()
        sources = ", ".join(sorted({s["source"] for s in data["sources"]}))
        return f"{data['answer']}\n\n(sources: {sources})"
    except requests.RequestException as exc:
        return (
            "knowledge_search is unavailable (RAG API is offline: "
            f"{type(exc).__name__}). Answer from your own knowledge and "
            "tell the user the knowledge base could not be reached."
        )


# --------------------------------------------------------------------------
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression element: {ast.dump(node)}")


@mcp.tool()
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression, e.g. "1/(60+1) + 1/(60+3)".
    Supports + - * / ** % and parentheses. Use for any numeric computation."""
    try:
        result = _safe_eval(ast.parse(expression, mode="eval"))
        return f"{expression} = {result:.6g}"
    except Exception as exc:
        return f"Calculator error: {exc}"


# --------------------------------------------------------------------------
@mcp.tool()
def get_current_time() -> str:
    """Get the current local date and time."""
    return datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------
@mcp.tool()
def save_report(title: str, content: str) -> str:
    """Save a markdown report to the reports/ directory.
    SENSITIVE ACTION: writes to disk — requires human approval."""
    REPORTS_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "report"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"{stamp}_{slug}.md"
    path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    return f"Report saved to {path}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
