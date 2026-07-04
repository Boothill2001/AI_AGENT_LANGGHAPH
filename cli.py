"""Terminal chat with the agent (backup demo if the UI misbehaves).

Run from the project root:
    python cli.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agent.runtime import AgentRuntime  # noqa: E402

BANNER = """
Research Copilot — LangGraph + MCP (type 'exit' to quit)
Try: Search the knowledge base for what RRF is, then calculate
     1/(60+1) + 1/(60+3), and save a short report about it.
"""


def render(steps) -> str | None:
    """Print steps; if an interrupt is pending return its tool name."""
    for s in steps:
        if s.kind == "tool_call":
            print(f"\n  [tool call] {s.tool}({s.text})")
        elif s.kind == "tool_result":
            preview = s.text if len(s.text) < 400 else s.text[:400] + "..."
            print(f"  [result]    {preview}")
        elif s.kind == "answer":
            print(f"\nAssistant: {s.text}")
        elif s.kind == "interrupt":
            print(f"\n  [HUMAN-IN-THE-LOOP] {s.text}")
            print(f"                      args: {s.payload}")
            return s.tool
    return None


def main() -> None:
    print(BANNER)
    print("Starting MCP server and connecting tools...")
    runtime = AgentRuntime()
    print(f"Connected. Tools: {[t.name for t in runtime.tools]}\n")

    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user or user.lower() in {"exit", "quit"}:
            break

        steps = runtime.send(user)
        while render(steps):  # loop while interrupts are pending
            answer = input("  Approve? [y/N]: ").strip().lower()
            steps = runtime.resume(approved=answer == "y")


if __name__ == "__main__":
    main()
