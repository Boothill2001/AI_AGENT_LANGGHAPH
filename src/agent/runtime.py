"""Synchronous facade over the async agent, for Streamlit and other sync callers.

Runs a private asyncio event loop in a background thread so the MCP client
(and its stdio subprocess) stays alive across Streamlit reruns.
"""

import asyncio
import threading
import uuid
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from .graph import build_graph


@dataclass
class StepEvent:
    """One renderable step of an agent turn."""
    kind: str                 # "tool_call" | "tool_result" | "answer" | "interrupt"
    text: str
    tool: str = ""
    payload: dict = field(default_factory=dict)


class AgentRuntime:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()
        self.graph, self.tools = self._run(build_graph())
        self.thread_id = str(uuid.uuid4())

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=300)

    # ------------------------------------------------------------------ API

    def send(self, user_message: str) -> list[StepEvent]:
        """Send a user message; returns rendered steps (may end in an interrupt)."""
        config = {"configurable": {"thread_id": self.thread_id}, "recursion_limit": 40}
        result = self._run(
            self.graph.ainvoke(
                {"messages": [HumanMessage(content=user_message)]}, config
            )
        )
        return self._collect_steps(result)

    def resume(self, approved: bool) -> list[StepEvent]:
        """Resume a run paused on a human-in-the-loop interrupt."""
        config = {"configurable": {"thread_id": self.thread_id}, "recursion_limit": 40}
        result = self._run(
            self.graph.ainvoke(Command(resume={"approved": approved}), config)
        )
        return self._collect_steps(result)

    def new_conversation(self) -> None:
        self.thread_id = str(uuid.uuid4())

    # ------------------------------------------------------------- internal

    def _collect_steps(self, result: dict) -> list[StepEvent]:
        steps: list[StepEvent] = []

        # Pending interrupt? (graph paused waiting for approval)
        pending = result.get("__interrupt__")

        # Walk this turn's messages backwards until the triggering HumanMessage
        turn: list = []
        for msg in reversed(result["messages"]):
            if isinstance(msg, HumanMessage):
                break
            turn.append(msg)
        turn.reverse()

        for msg in turn:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for call in msg.tool_calls:
                    steps.append(StepEvent(
                        kind="tool_call", tool=call["name"],
                        text=str(call["args"]), payload=call["args"],
                    ))
            elif isinstance(msg, ToolMessage):
                steps.append(StepEvent(kind="tool_result", text=str(msg.content)))
            elif isinstance(msg, AIMessage) and msg.content:
                steps.append(StepEvent(kind="answer", text=str(msg.content)))

        if pending:
            info = pending[0].value if isinstance(pending, (list, tuple)) else pending.value
            steps.append(StepEvent(
                kind="interrupt",
                tool=info.get("tool", "?"),
                text=info.get("question", "Approve this action?"),
                payload=info.get("args", {}),
            ))
        return steps
