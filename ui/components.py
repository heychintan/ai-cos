"""Reusable UI components using standard Streamlit widgets."""
import streamlit as st


def render_header(run_status: str = "idle") -> None:
    status_map = {
        "idle": "⬜ Idle",
        "fetching": "🔄 Fetching data…",
        "generating": "🔄 Generating…",
        "done": "✅ Done",
        "error": "❌ Error",
    }
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("CoSN Agent Dashboard")
        st.caption("Newsletter Automation")
    with col2:
        st.write("")
        st.write(status_map.get(run_status, "⬜ Idle"))


def render_source_card(icon: str, name: str, description: str, status: str, enabled: bool) -> None:
    status_map = {
        "ok": "✅ Fetched",
        "error": "❌ Failed",
        "idle": "○ Not fetched",
        "disabled": "— Disabled",
    }
    st.markdown(f"**{icon} {name}**")
    st.caption(description)
    st.caption(status_map.get(status, "○ Not fetched"))


def render_step_indicator(run_status: str) -> None:
    steps = {
        "idle":       "○ Fetch  →  ○ Generate  →  ○ Done",
        "fetching":   "🔄 Fetch  →  ○ Generate  →  ○ Done",
        "generating": "✅ Fetch  →  🔄 Generate  →  ○ Done",
        "done":       "✅ Fetch  →  ✅ Generate  →  ✅ Done",
        "error":      "✅ Fetch  →  ❌ Generate  →  — Done",
    }
    st.caption(steps.get(run_status, steps["idle"]))


def section_label(text: str) -> None:
    st.markdown(f"**{text}**")


def cos_divider() -> None:
    st.divider()


def info_box(text: str) -> None:
    st.info(text, icon="ℹ️")


def file_chips(files: list) -> None:
    if files:
        st.caption("  ·  ".join(f"📄 {f.name}" for f in files))
