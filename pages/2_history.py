"""
📋 Run History — In-session log of automation runs.
Cleared when the browser session ends.
"""
import streamlit as st
from datetime import timezone
from ui.styles import inject_styles
from ui.components import section_label, cos_divider

st.set_page_config(
    page_title="Run History — CoSN Agent",
    page_icon="📋",
    layout="wide",
)
inject_styles()

st.markdown("## 📋 Run History")
st.markdown("In-session log of automation runs. Clears when you close or reload this tab.")
cos_divider()

history: list[dict] = st.session_state.get("run_history", [])

if not history:
    st.markdown(
        '<div class="cos-info">No runs recorded yet. Go to the <strong>Dashboard</strong> and click <em>Run Automation</em>.</div>',
        unsafe_allow_html=True,
    )
else:
    section_label(f"{len(history)} run(s) this session")

    for idx, run in enumerate(reversed(history)):
        ts = run.get("timestamp", "Unknown time")
        model = run.get("model", "—")
        status = run.get("status", "unknown")
        sources = run.get("sources", [])
        error = run.get("error", "")
        output = run.get("output", "")

        badge = (
            '<span class="badge-success">✓ Success</span>'
            if status == "done"
            else '<span class="badge-error">✕ Error</span>'
        )
        sources_str = ", ".join(sources) if sources else "none"

        with st.expander(f"Run #{len(history) - idx} — {ts}", expanded=(idx == 0)):
            st.markdown(
                f"""
                | Field | Value |
                |---|---|
                | **Status** | {badge} |
                | **Model** | `{model}` |
                | **Sources** | {sources_str} |
                | **Time** | {ts} |
                """,
                unsafe_allow_html=True,
            )

            if error:
                st.error(f"Error: {error}")

            if output:
                st.markdown("**Generated Output (preview)**")
                st.markdown(
                    f'<div class="cos-preview">{output[:2000]}{"…" if len(output) > 2000 else ""}</div>',
                    unsafe_allow_html=True,
                )

    cos_divider()
    if st.button("Clear History", type="secondary"):
        st.session_state["run_history"] = []
        st.rerun()
