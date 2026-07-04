# Research Copilot — LangGraph Agent + MCP + Human-in-the-Loop

A production-style **AI agent** demonstrating the core patterns of agentic systems:
a **planner/executor loop** built with **LangGraph**, tools served over the
**Model Context Protocol (MCP)**, **human-in-the-loop approval** for sensitive
actions, and guardrails (iteration caps, tool-error recovery, graceful degradation).

Works as an ecosystem with my [Advanced RAG project](https://github.com/Boothill2001/RAG_project):
the agent's `knowledge_search` tool calls that RAG API as one of its tools.

## Architecture

```
 User ──► Streamlit chat (app.py)  /  CLI (cli.py)
            │
            ▼
   LangGraph StateGraph (src/agent/graph.py)
   ┌─────────────────────────────────────────────────┐
   │   planner (DeepSeek) — decides the next action   │
   │      │ tool_calls                     ▲          │
   │      ▼                                │ results  │
   │   tool executor ───────────────────────┘         │
   │      │                                           │
   │      │  sensitive tool (save_report)?            │
   │      └─► interrupt() — graph PAUSES until a      │
   │          human approves or rejects               │
   └───────────────┬─────────────────────────────────┘
                   │ MCP client (stdio)
                   ▼
   MCP server (mcp_server/server.py — FastMCP)
   ├── knowledge_search  → Advanced RAG API (localhost:8000)
   ├── calculator        → safe AST math evaluation
   ├── get_current_time
   └── save_report       → writes markdown to reports/  ⚠ gated
```

## Key patterns demonstrated

| Pattern | Where |
|---|---|
| Planner/executor agent loop | `src/agent/graph.py` — LangGraph `StateGraph`, conditional edges on `tool_calls` |
| Tool-calling / function calling | DeepSeek via `langchain-openai`, `bind_tools` over MCP-loaded tools |
| MCP integration | Real MCP server (`FastMCP`, stdio) + `langchain-mcp-adapters` client |
| Human-in-the-loop | LangGraph `interrupt()` before sensitive tools; resume with `Command(resume=...)`; approval UI in Streamlit |
| Guardrails | Iteration cap (forces a final answer), per-tool exception handling, safe AST calculator (no `eval`) |
| Graceful degradation | RAG API offline → tool returns an explanatory message, agent finishes the rest of the task |
| Multi-service ecosystem | `knowledge_search` consumes the [RAG project](https://github.com/Boothill2001/RAG_project)'s FastAPI |

## Quickstart

```bash
# 1. Install (Python 3.10+)
python -m venv .venv
.venv\Scripts\activate            # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Configure the LLM
copy .env.example .env            # put your DeepSeek key in .env

# 3. (Optional but recommended) start the RAG API in the RAG_project repo,
#    so the knowledge_search tool has a backend:
#    cd ../RAG_project && uvicorn api.main:app --port 8000

# 4. Chat with the agent
streamlit run app.py              # web UI
python cli.py                     # or terminal
```

## Demo scenario

Ask the agent:

> Search the knowledge base for what Reciprocal Rank Fusion is, then calculate
> 1/(60+1) + 1/(60+3), and save a short report titled "RRF summary".

Watch it: **plan** → call `knowledge_search` (hits the RAG API) → call
`calculator` → attempt `save_report` → **pause for your approval** → write the
report → synthesize a final answer describing every step. Reject the approval
instead, and it explains the rejection gracefully.

## Project layout

```
mcp_server/server.py   # FastMCP stdio server: the 4 tools
src/agent/config.py    # LLM credentials, MCP launch config, guardrail knobs
src/agent/graph.py     # LangGraph planner/executor + interrupt-based HITL
src/agent/runtime.py   # sync facade w/ background event loop (for Streamlit)
app.py                 # Streamlit chat: step timeline + Approve/Reject buttons
cli.py                 # terminal chat (backup demo)
```

## Design decisions

- **Why LangGraph over a plain ReAct loop?** Explicit graph = controllable:
  conditional edges, checkpointed state, `interrupt()` for human approval, and
  replayable threads. A hand-rolled while-loop gives you none of that.
- **Why MCP instead of local `@tool` functions?** MCP decouples tools from the
  agent: the same server can serve Claude Desktop, other agents, or other teams
  — with a standard schema and transport. This mirrors how enterprises expose
  internal APIs to LLMs.
- **Why interrupt-based HITL?** Sensitive actions (writes, emails, payments)
  must not depend on the model "choosing" to ask. The *graph* enforces the
  pause — the model cannot bypass it.
- **Provider-agnostic:** DeepSeek today; swapping to Claude/GPT is one line in
  `config.py`.

## Author

**Nguyen Minh Tri** — Senior AI Engineer (GenAI / LLM applications)
📧 minhtri.cm2001@gmail.com · [RAG project](https://github.com/Boothill2001/RAG_project)
