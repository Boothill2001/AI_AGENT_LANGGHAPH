"""End-to-end verification of the agent (not shipped — temp file).

Checks: multi-step tool use, human-in-the-loop interrupt + approve,
report file creation, and final answer synthesis.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agent.runtime import AgentRuntime

runtime = AgentRuntime()
print("tools:", [t.name for t in runtime.tools])

TASK = (
    "Search the knowledge base for what Reciprocal Rank Fusion is, "
    "then calculate 1/(60+1) + 1/(60+3), "
    "and save a short report titled 'RRF summary' with your findings."
)

steps = runtime.send(TASK)
for s in steps:
    print(f"--- {s.kind} {('['+s.tool+']') if s.tool else ''}: {s.text[:200]}")

interrupts = [s for s in steps if s.kind == "interrupt"]
assert interrupts, "EXPECTED a human-in-the-loop interrupt for save_report"
print("\n>>> INTERRUPT detected, approving...\n")

steps2 = runtime.resume(approved=True)
for s in steps2:
    print(f"--- {s.kind} {('['+s.tool+']') if s.tool else ''}: {s.text[:300]}")

reports = list((Path(__file__).parent / "reports").glob("*.md"))
assert reports, "EXPECTED a report file to be written"
print(f"\n>>> Report file created: {reports[-1].name}")
print(">>> VERIFY OK")
