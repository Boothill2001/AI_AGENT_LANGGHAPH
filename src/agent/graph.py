"""LangGraph agent: planner/executor loop over MCP tools with human-in-the-loop.

Graph shape:

    START ─► planner ──(tool_calls?)──► tools ─► planner ─► ... ─► END
                                          │
                       sensitive tool ────┴─► interrupt() — pauses the graph
                                              until a human approves/rejects

- planner: DeepSeek decides the next action (call a tool or answer).
- tools:   executes MCP tools; sensitive tools trigger a LangGraph interrupt,
           so the run pauses and resumes only after human approval.
- guardrail: MAX_AGENT_ITERATIONS caps the loop; on the last iteration the
           planner is forced to answer without tools.
"""

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import interrupt

from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    MAX_AGENT_ITERATIONS,
    MCP_SERVER,
    SENSITIVE_TOOLS,
)

SYSTEM_PROMPT = """You are a Research Copilot — a planner/executor agent.

You have tools (provided via MCP). For each user request:
1. Think about which tools are needed and in what order.
2. Call tools one step at a time; use each tool result to decide the next step.
3. When you have everything, write a clear final answer summarizing what you did.

Rules:
- Use knowledge_search for any factual question about AI/RAG/LLM engineering.
- Use calculator for ANY arithmetic — never compute numbers yourself.
- save_report writes to disk and requires human approval; only call it when
  the user explicitly asks to save/write a report.
- If a tool fails or is unavailable, say so honestly and continue with the rest."""


def _to_text(output) -> str:
    """Flatten MCP content blocks ([{'type':'text','text':...}]) to plain text."""
    if isinstance(output, list):
        parts = []
        for item in output:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(output)


async def build_graph():
    """Connect to the MCP server, load its tools, and compile the agent graph.

    Returns (graph, tools). The MCP client keeps the stdio server subprocess
    alive for the lifetime of the returned graph.
    """
    client = MultiServerMCPClient(MCP_SERVER)
    tools = await client.get_tools()
    tools_by_name = {t.name: t for t in tools}

    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.1,
        timeout=90,
    )
    llm_with_tools = llm.bind_tools(tools)

    # ---- nodes ------------------------------------------------------------

    async def planner(state: MessagesState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        # Guardrail: count how many tool rounds this turn has already used
        rounds = sum(
            1 for m in state["messages"]
            if isinstance(m, AIMessage) and m.tool_calls
        )
        if rounds >= MAX_AGENT_ITERATIONS:
            messages.append(SystemMessage(
                content="Iteration limit reached. Answer NOW with what you have; "
                        "do not call any more tools."
            ))
            response = await llm.ainvoke(messages)  # tools unbound
        else:
            response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    async def tool_executor(state: MessagesState):
        last = state["messages"][-1]
        results = []
        for call in last.tool_calls:
            name, args = call["name"], call["args"]

            # Human-in-the-loop gate for sensitive tools
            if name in SENSITIVE_TOOLS:
                decision = interrupt(
                    {"tool": name, "args": args,
                     "question": f"Agent wants to run sensitive tool '{name}'. Approve?"}
                )
                if not (isinstance(decision, dict) and decision.get("approved")):
                    results.append(ToolMessage(
                        content="ACTION REJECTED by the human operator. "
                                "Do not retry; explain this in your final answer.",
                        tool_call_id=call["id"],
                    ))
                    continue

            try:
                output = await tools_by_name[name].ainvoke(args)
            except Exception as exc:  # tool crash must not kill the agent
                output = f"Tool '{name}' failed: {type(exc).__name__}: {exc}"
            results.append(ToolMessage(content=_to_text(output), tool_call_id=call["id"]))
        return {"messages": results}

    def route(state: MessagesState):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    # ---- graph ------------------------------------------------------------

    builder = StateGraph(MessagesState)
    builder.add_node("planner", planner)
    builder.add_node("tools", tool_executor)
    builder.add_edge(START, "planner")
    builder.add_conditional_edges("planner", route, {"tools": "tools", END: END})
    builder.add_edge("tools", "planner")

    # Checkpointer is required for interrupt/resume (human-in-the-loop)
    graph = builder.compile(checkpointer=MemorySaver())
    return graph, tools
