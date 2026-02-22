"""📅 Content Calendar — month grid of past drafts and scheduled future runs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import streamlit as st
from streamlit_calendar import calendar

from ui.styles import inject_styles
from agent.task import fmt_interval

st.set_page_config(page_title="Content Calendar — CoSN Agent", page_icon="📅", layout="wide")
inject_styles()

st.title("📅 Content Calendar")

tasks: list[dict] = st.session_state.get("tasks", [])

# ── Build events ───────────────────────────────────────────────────────────────

events: list[dict] = []
now = datetime.now(timezone.utc)
horizon = now + timedelta(days=30)

upcoming_count = 0

for task in tasks:
    task_id = task["id"]
    task_name = task["name"]

    # Past events — one per completed output
    for idx, output in enumerate(task.get("outputs", [])):
        ts_str = output.get("timestamp", "")
        try:
            # "YYYY-MM-DD HH:MM UTC"
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        events.append({
            "id":    f"past:{task_id}:{idx}",
            "title": task_name,
            "start": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "backgroundColor": "#2E7D32",
            "borderColor":     "#2E7D32",
            "textColor":       "#ffffff",
        })

    # Future events — project from next_run for 30 days
    if not task.get("enabled"):
        continue
    next_run = task.get("next_run")
    interval = task.get("interval", 86400)
    if not next_run or interval <= 0:
        continue

    # next_run may be a datetime or a string; normalise
    if isinstance(next_run, str):
        try:
            next_run = datetime.fromisoformat(next_run)
        except ValueError:
            continue
    if next_run.tzinfo is None:
        next_run = next_run.replace(tzinfo=timezone.utc)

    projected = next_run
    while projected <= horizon:
        upcoming_count += 1
        events.append({
            "id":    f"future:{task_id}:{projected.isoformat()}",
            "title": f"🔵 {task_name}",
            "start": projected.strftime("%Y-%m-%dT%H:%M:%S"),
            "backgroundColor": "#1565C0",
            "borderColor":     "#1565C0",
            "textColor":       "#ffffff",
        })
        projected += timedelta(seconds=interval)

st.caption(
    f"{len(tasks)} task(s) · {upcoming_count} upcoming run(s) in next 30 days"
)

# ── Calendar component ─────────────────────────────────────────────────────────

calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left":   "prev,next today",
        "center": "title",
        "right":  "",
    },
    "selectable": True,
    "editable":   False,
    "height":     600,
}

custom_css = """
.fc-event { cursor: pointer; font-size: 0.78rem; }
"""

result = calendar(
    events=events,
    options=calendar_options,
    custom_css=custom_css,
    key="content_calendar",
)

# Capture click via the returned dict
if result and result.get("eventClick"):
    clicked_id = result["eventClick"]["event"]["id"]
    st.session_state["cal_selected"] = clicked_id

selected_id: str = st.session_state.get("cal_selected", "")

# ── Draft / detail panel ───────────────────────────────────────────────────────

st.divider()

if not selected_id:
    st.info("Click an event to see details.", icon="👆")
else:
    parts = selected_id.split(":", 2)
    kind = parts[0] if parts else ""

    # Build quick lookup maps
    tasks_by_id = {t["id"]: t for t in tasks}

    if kind == "past" and len(parts) == 3:
        task_id, idx_str = parts[1], parts[2]
        task = tasks_by_id.get(task_id)
        if task is None:
            st.warning("Task no longer in session.")
        else:
            try:
                output = task["outputs"][int(idx_str)]
            except (IndexError, ValueError):
                st.warning("Output not found.")
            else:
                st.subheader(f"📄 Draft — {task['name']}")
                st.caption(f"Run timestamp: {output.get('timestamp', '—')}")

                if output.get("sources_used"):
                    st.caption("Sources: " + " · ".join(output["sources_used"]))

                with st.expander("Draft text", expanded=True):
                    st.markdown(output.get("text", "_(no text)_"))

                if output.get("docx_bytes"):
                    from datetime import datetime as _dt, timezone as _tz
                    date_str = _dt.now(_tz.utc).strftime("%Y-%m-%d")
                    st.download_button(
                        label="⬇️ Download .docx",
                        data=output["docx_bytes"],
                        file_name=f"CoSN_{task['name'].replace(' ', '_')}_{date_str}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"cal_dl_{task_id}_{idx_str}",
                    )

    elif kind == "future" and len(parts) == 3:
        task_id = parts[1]
        scheduled_iso = parts[2]
        task = tasks_by_id.get(task_id)
        if task is None:
            st.warning("Task no longer in session.")
        else:
            st.subheader(f"🔵 Scheduled Run — {task['name']}")
            try:
                sched_dt = datetime.fromisoformat(scheduled_iso)
                st.caption(f"Scheduled: {sched_dt.strftime('%b %d, %Y at %H:%M UTC')}")
            except ValueError:
                st.caption(f"Scheduled: {scheduled_iso}")

            st.caption(f"Interval: every {fmt_interval(task['interval'])}")

            src = task.get("sources", {})
            enabled_sources = []
            if src.get("luma", {}).get("enabled"):
                enabled_sources.append(f"📅 Luma Events ({src['luma'].get('days', 21)} days)")
            if src.get("spotify", {}).get("enabled"):
                enabled_sources.append(f"🎙️ Spotify Podcast ({src['spotify'].get('days', 7)} days)")
            if src.get("webflow", {}).get("enabled"):
                enabled_sources.append("💼 Webflow Jobs")
            if src.get("webflow_blogs", {}).get("enabled"):
                enabled_sources.append("📰 Webflow Blogs")

            if enabled_sources:
                st.markdown("**Sources:** " + " · ".join(enabled_sources))
            else:
                st.markdown("**Sources:** _(none enabled)_")
    else:
        st.info("Click an event to see details.", icon="👆")
