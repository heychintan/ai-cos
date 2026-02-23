"""📋 Task Detail — all runs for a single task, with edit dialog."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from ui.styles import inject_styles
from agent.task import (
    fmt_interval, fmt_dt, schedule_next,
    INTERVAL_PRESETS, MIN_INTERVAL,
)
from agent.claude import AVAILABLE_MODELS

st.set_page_config(page_title="Task Detail — CoSN Agent", page_icon="📋", layout="wide")
inject_styles()

# ── Resolve task from session state ───────────────────────────────────────────

tasks: list[dict] = st.session_state.get("tasks", [])
task_id: str = st.session_state.get("detail_task_id", "")
task = next((t for t in tasks if t["id"] == task_id), None)

if task is None:
    st.warning("Task not found. It may have been deleted or the session was reset.")
    if st.button("← Back to Dashboard"):
        st.switch_page("app.py")
    st.stop()

# ── Edit dialog ────────────────────────────────────────────────────────────────

# Map interval seconds → preset label (for pre-selecting the dropdown)
_preset_by_val = {v: k for k, v in INTERVAL_PRESETS.items()}


@st.dialog("Edit Task", width="large")
def _edit_dialog(t: dict) -> None:
    src = t["sources"]

    name = st.text_input("Task name *", value=t["name"])
    instructions = st.text_area(
        "Instructions",
        value=t.get("instructions", ""),
        height=90,
    )

    st.divider()
    col_src, col_sched = st.columns(2)

    with col_src:
        st.markdown("**Sources**")
        luma_en   = st.checkbox("📅 Luma Events",   value=src.get("luma", {}).get("enabled", False),    key="e_luma_en")
        luma_days = st.slider("Look-ahead (days)", 7, 60,
                              src.get("luma", {}).get("days", 21), key="e_luma_days") if luma_en else src.get("luma", {}).get("days", 21)
        sp_en     = st.checkbox("🎙️ Spotify Podcast", value=src.get("spotify", {}).get("enabled", False), key="e_sp_en")
        sp_days   = st.slider("Look-back (days)", 1, 30,
                              src.get("spotify", {}).get("days", 7), key="e_sp_days") if sp_en else src.get("spotify", {}).get("days", 7)
        wf_en     = st.checkbox("💼 Webflow Jobs",   value=src.get("webflow", {}).get("enabled", False),        key="e_wf_en")
        wf_blog_en= st.checkbox("📰 Webflow Blogs",  value=src.get("webflow_blogs", {}).get("enabled", False),  key="e_wf_blog_en")

    with col_sched:
        st.markdown("**Schedule & Model**")
        current_preset = _preset_by_val.get(t["interval"], "Custom")
        preset_options = list(INTERVAL_PRESETS.keys()) + ["Custom"]
        preset = st.selectbox(
            "Repeat interval",
            preset_options,
            index=preset_options.index(current_preset),
            key="e_preset",
        )
        if preset == "Custom":
            interval = st.number_input(
                "Seconds (min 60)", min_value=60, value=t["interval"], step=60, key="e_interval"
            )
        else:
            interval = INTERVAL_PRESETS[preset]
        st.caption(f"Repeats every **{fmt_interval(int(interval))}**")

        model = st.selectbox(
            "Claude model",
            AVAILABLE_MODELS,
            index=AVAILABLE_MODELS.index(t["model"]) if t["model"] in AVAILABLE_MODELS else 0,
            key="e_model",
        )

    st.write("")
    if st.button("Save Changes", type="primary", use_container_width=True):
        if not name.strip():
            st.error("Task name is required.")
            return

        interval = max(int(interval), MIN_INTERVAL)
        interval_changed = interval != t["interval"]

        # Mutate task in-place (it's the same object in session_state["tasks"])
        t["name"]         = name.strip()
        t["instructions"] = instructions
        t["interval"]     = interval
        t["model"]        = model
        t["sources"]["luma"]          = {"enabled": luma_en,    "days": luma_days}
        t["sources"]["spotify"]       = {"enabled": sp_en,      "days": sp_days}
        t["sources"]["webflow"]       = {"enabled": wf_en}
        t["sources"]["webflow_blogs"] = {"enabled": wf_blog_en}

        # Re-schedule if interval changed and task is active
        if interval_changed and t.get("enabled"):
            schedule_next(t)

        st.rerun()


# ── Header row: back | title | edit ───────────────────────────────────────────

col_back, col_title, col_edit = st.columns([1, 5, 1])

with col_back:
    st.write("")
    if st.button("← Back", use_container_width=True):
        st.switch_page("app.py")

with col_title:
    st.title(f"📋 {task['name']}")

with col_edit:
    st.write("")
    if st.button("✏️ Edit", use_container_width=True, type="secondary"):
        _edit_dialog(task)

# ── Task metadata ──────────────────────────────────────────────────────────────

st.divider()

meta_cols = st.columns(4)

status_display = {
    "idle":    "○ Idle",
    "running": "🔄 Running",
    "done":    "✅ Done",
    "error":   "❌ Error",
}.get(task["status"], "—")

meta_cols[0].metric("Status",   status_display)
meta_cols[1].metric("Interval", fmt_interval(task["interval"]))
meta_cols[2].metric("Last run", fmt_dt(task.get("last_run")))
meta_cols[3].metric("Next run", fmt_dt(task.get("next_run")) if task["enabled"] else "Paused")

src = task["sources"]
source_tags = []
if src.get("luma", {}).get("enabled"):
    source_tags.append(f"📅 Luma Events ({src['luma'].get('days', 21)}d)")
if src.get("spotify", {}).get("enabled"):
    source_tags.append(f"🎙️ Spotify ({src['spotify'].get('days', 7)}d)")
if src.get("webflow", {}).get("enabled"):
    source_tags.append("💼 Webflow Jobs")
if src.get("webflow_blogs", {}).get("enabled"):
    source_tags.append("📰 Webflow Blogs")

st.caption("**Sources:** " + (" · ".join(source_tags) if source_tags else "_(none enabled)_"))
st.caption(f"**Model:** `{task.get('model', '—')}`")

if task.get("instructions"):
    with st.expander("Instructions", expanded=False):
        st.markdown(task["instructions"])

if task.get("last_error"):
    st.error(f"Last error: {task['last_error']}")

# ── Runs / Outputs ─────────────────────────────────────────────────────────────

st.divider()

outputs: list[dict] = task.get("outputs", [])

if not outputs:
    st.info("No runs yet. Go to the Dashboard and click ▶ to trigger a run.", icon="ℹ️")
else:
    st.subheader(f"Runs ({len(outputs)})")

    for idx, output in enumerate(outputs):
        run_num = len(outputs) - idx
        ts = output.get("timestamp", "—")
        sources_used = output.get("sources_used", [])

        with st.expander(f"Run #{run_num} · {ts}", expanded=(idx == 0)):
            if sources_used:
                st.caption("Sources: " + " · ".join(sources_used))

            st.markdown(output.get("text", "_(no output text)_"))

            if output.get("docx_bytes"):
                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                safe_name = task["name"].replace(" ", "_")
                st.download_button(
                    label="⬇️ Download .docx",
                    data=output["docx_bytes"],
                    file_name=f"CoSN_{safe_name}_Run{run_num}_{date_str}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_detail_{task_id}_{idx}",
                )
