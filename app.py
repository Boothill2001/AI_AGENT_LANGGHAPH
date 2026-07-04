"""Streamlit chat UI for the LangGraph + MCP Research Copilot.

Run from the project root:
    streamlit run app.py
"""

import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agent.runtime import AgentRuntime  # noqa: E402

st.set_page_config(page_title="Research Copilot — LangGraph + MCP", page_icon="🤖", layout="wide")

st.markdown("""
<style>
  /* Header banner */
  .agent-hero {
    background: linear-gradient(120deg, #4a3e8f 0%, #35306b 60%, #232042 100%);
    border-radius: 16px; padding: 26px 32px; margin-bottom: 8px; color: #f0eefa;
  }
  .agent-hero h1 { margin: 0; font-size: 1.7rem; color: #ffffff; }
  .agent-hero p  { margin: 6px 0 0; color: #cdc8e8; font-size: .95rem; }
  .agent-hero .chips { margin-top: 12px; }
  .agent-hero .chip {
    display: inline-block; background: rgba(255,255,255,.13);
    border: 1px solid rgba(255,255,255,.28); border-radius: 999px;
    padding: 3px 13px; margin-right: 8px; font-size: .8rem; font-weight: 600;
  }
  /* Tool-call step card */
  .tool-step {
    border-left: 4px solid #7c6fd0; background: rgba(124,111,208,.08);
    border-radius: 0 10px 10px 0; padding: 8px 14px; margin: 6px 0;
    font-size: .92rem;
  }
  .tool-step code { color: #a99ef0; font-weight: 700; }
  /* Chat width */
  .stChatMessage { border-radius: 14px; }
</style>
<div class="agent-hero">
  <h1>🤖 Research Copilot — LangGraph + MCP</h1>
  <p>Planner/executor agent (DeepSeek) · tools served over Model Context Protocol · human-in-the-loop approval for sensitive actions</p>
  <div class="chips">
    <span class="chip">🕸️ LangGraph</span>
    <span class="chip">🔌 MCP</span>
    <span class="chip">✋ Human-in-the-loop</span>
    <span class="chip">🛡️ Guardrails</span>
  </div>
</div>
""", unsafe_allow_html=True)


def prettify(text: str) -> str:
    """Make model output render nicely in Streamlit.

    DeepSeek occasionally emits LaTeX delimiters Streamlit doesn't render
    (\\[..\\], \\(..\\), [ \\frac.. ]). Convert them to $-math (KaTeX) so
    formulas display properly instead of showing raw markup.
    """
    text = re.sub(r"\\\[(.+?)\\\]", r"\n$$\1$$\n", text, flags=re.S)
    text = re.sub(r"\\\((.+?)\\\)", r"$\1$", text, flags=re.S)
    # Bare [ ... ] blocks that clearly contain LaTeX commands
    text = re.sub(
        r"\[\s*((?:[^\[\]]*?\\(?:frac|text|sum|sqrt|cdot|times)[^\[\]]*?))\s*\]",
        r"\n$$\1$$\n", text, flags=re.S,
    )
    return text

# --- runtime (created once, survives reruns) -------------------------------
if "runtime" not in st.session_state:
    with st.spinner("Starting MCP server, loading tools, compiling graph..."):
        st.session_state.runtime = AgentRuntime()
    st.session_state.history = []          # list of {"role", "steps" | "text"}
    st.session_state.pending_interrupt = None

runtime: AgentRuntime = st.session_state.runtime

# --- sidebar ----------------------------------------------------------------
with st.sidebar:
    st.header("Agent")
    st.write("**Tools (via MCP):**")
    for t in runtime.tools:
        icon = "⚠️" if t.name == "save_report" else "🔧"
        st.write(f"{icon} `{t.name}`")
    st.divider()
    st.markdown(
        "**Try asking:**\n"
        "- Search the knowledge base: what is RRF?\n"
        "- Calculate 1/(60+1) + 1/(60+3)\n"
        "- *Multi-step:* Search what RRF is, calculate the RRF score of a chunk "
        "ranked #1 by dense and #3 by BM25 (k=60), then **save a short report**.\n"
    )
    st.divider()
    if st.button("🗑️ New conversation"):
        runtime.new_conversation()
        st.session_state.history = []
        st.session_state.pending_interrupt = None
        st.rerun()


def render_steps(steps) -> None:
    """Render one agent turn as a timeline of steps."""
    for s in steps:
        if s.kind == "tool_call":
            args = ", ".join(f"{k}={str(v)[:60]!r}" for k, v in s.payload.items())
            st.markdown(
                f'<div class="tool-step">🔧 Calling <code>{s.tool}</code>({args})</div>',
                unsafe_allow_html=True,
            )
        elif s.kind == "tool_result":
            with st.expander("↳ tool result", expanded=False):
                st.text(s.text[:1500] + ("..." if len(s.text) > 1500 else ""))
        elif s.kind == "answer":
            st.markdown(prettify(s.text))


# --- history ----------------------------------------------------------------
for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        if turn["role"] == "user":
            st.markdown(turn["text"])
        else:
            render_steps(turn["steps"])

# --- pending human-in-the-loop approval --------------------------------------
if st.session_state.pending_interrupt:
    info = st.session_state.pending_interrupt
    with st.chat_message("assistant"):
        st.warning(f"⚠️ **Human approval required** — agent wants to run `{info.tool}`")
        st.code(str(info.payload), language="json")
        col1, col2, _ = st.columns([1, 1, 4])
        approve = col1.button("✅ Approve", type="primary")
        reject = col2.button("❌ Reject")
        if approve or reject:
            st.session_state.pending_interrupt = None
            with st.spinner("Resuming agent..."):
                steps = runtime.resume(approved=approve)
            interrupts = [s for s in steps if s.kind == "interrupt"]
            st.session_state.history.append(
                {"role": "assistant", "steps": [s for s in steps if s.kind != "interrupt"]}
            )
            st.session_state.pending_interrupt = interrupts[0] if interrupts else None
            st.rerun()

# --- input -------------------------------------------------------------------
prompt_disabled = st.session_state.pending_interrupt is not None
if question := st.chat_input(
    "Ask the copilot... (approval pending above)" if prompt_disabled
    else "Ask the copilot to research, calculate, or write a report...",
    disabled=prompt_disabled,
):
    st.session_state.history.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Planning → calling tools → reasoning..."):
            steps = runtime.send(question)
        interrupts = [s for s in steps if s.kind == "interrupt"]
        visible = [s for s in steps if s.kind != "interrupt"]
        render_steps(visible)

    st.session_state.history.append({"role": "assistant", "steps": visible})
    st.session_state.pending_interrupt = interrupts[0] if interrupts else None
    if interrupts:
        st.rerun()
