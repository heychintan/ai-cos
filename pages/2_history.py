"""📋 Run History — In-session log of automation runs."""
import streamlit as st
from ui.styles import inject_styles

st.set_page_config(page_title="Run History — CoSN Agent", page_icon="📋", layout="centered")
inject_styles()

st.title("📋 Run History")
st.caption("In-session log of automation runs. Clears when you close or reload this tab.")
st.divider()

history: list = st.session_state.get("run_history", [])

if not history:
    st.info("No runs recorded yet. Go to the **Dashboard** and click **▶ Run Automation**.", icon="ℹ️")
else:
    st.caption(f"{len(history)} run(s) this session")

    for idx, run in enumerate(reversed(history)):
        ts      = run.get("timestamp", "Unknown")
        model   = run.get("model", "—")
        status  = run.get("status", "unknown")
        sources = ", ".join(run.get("sources", [])) or "none"
        error   = run.get("error", "")
        output  = run.get("output", "")
        icon    = "✅" if status == "done" else "❌"

        with st.expander(f"{icon} Run #{len(history) - idx} — {ts}", expanded=(idx == 0)):
            st.markdown(f"**Status:** {icon} {status.title()}  \n**Model:** `{model}`  \n**Sources:** {sources}  \n**Time:** {ts}")
            if error:
                st.error(f"Error: {error}")
            if output:
                st.markdown("**Output preview:**")
                st.markdown(output[:2000] + ("…" if len(output) > 2000 else ""))

    st.divider()
    if st.button("Clear History", type="secondary"):
        st.session_state["run_history"] = []
        st.rerun()
