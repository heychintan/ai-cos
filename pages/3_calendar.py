"""📅 Content Calendar — month grid of all scheduled instances and completed drafts."""
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

# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_dt(value) -> datetime | None:
    """Parse a datetime from an ISO string or datetime object; always UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        return None


# ── Build events ───────────────────────────────────────────────────────────────

events: list[dict] = []
now = datetime.now(timezone.utc)
horizon = now + timedelta(days=30)

upcoming_count = 0
past_slot_count = 0

for task in tasks:
    task_id   = task["id"]
    task_name = task["name"]
    interval  = task.get("interval", 86400)

    # ── Completed runs — green ─────────────────────────────────────────────────
    for idx, output in enumerate(task.get("outputs", [])):
        ts_str = output.get("timestamp", "")
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        events.append({
            "id":              f"past:{task_id}:{idx}",
            "title":           f"✅ {task_name}",
            "start":           dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "backgroundColor": "#2E7D32",
            "borderColor":     "#2E7D32",
            "textColor":       "#ffffff",
        })

    # ── Scheduled instances — blue (past = light, future = dark) ──────────────
    if not task.get("enabled") or interval <= 0:
        continue

    # Anchor: use created_at, fall back to next_run - interval, then now
    anchor = _parse_dt(task.get("created_at"))
    if anchor is None:
        next_run = _parse_dt(task.get("next_run"))
        anchor = (next_run - timedelta(seconds=interval)) if next_run else now

    projected = anchor
    while projected <= horizon:
        is_future = projected >= now
        if is_future:
            upcoming_count += 1
            color      = "#1565C0"
            text_color = "#ffffff"
            title      = f"🔵 {task_name}"
        else:
            past_slot_count += 1
            color      = "#90CAF9"
            text_color = "#1a1a1a"
            title      = task_name

        events.append({
            "id":              f"scheduled:{task_id}:{projected.isoformat()}",
            "title":           title,
            "start":           projected.strftime("%Y-%m-%dT%H:%M:%S"),
            "backgroundColor": color,
            "borderColor":     color,
            "textColor":       text_color,
        })
        projected += timedelta(seconds=interval)

st.caption(
    f"{len(tasks)} task(s) · {upcoming_count} upcoming run(s) in next 30 days"
)
st.caption(
    "🟦 Light blue = scheduled slot  ·  🔵 Dark blue = upcoming  ·  🟩 Green = completed draft"
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

# Capture click
if result and result.get("eventClick"):
    clicked_id = result["eventClick"]["event"]["id"]
    st.session_state["cal_selected"] = clicked_id

selected_id: str = st.session_state.get("cal_selected", "")

# ── Detail panel ───────────────────────────────────────────────────────────────

st.divider()

tasks_by_id = {t["id"]: t for t in tasks}

if not selected_id:
    st.info("Click an event to see details.", icon="👆")
else:
    parts = selected_id.split(":", 2)
    kind  = parts[0] if parts else ""

    # ── Completed run ──────────────────────────────────────────────────────────
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
                    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    st.download_button(
                        label="⬇️ Download .docx",
                        data=output["docx_bytes"],
                        file_name=f"CoSN_{task['name'].replace(' ', '_')}_{date_str}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"cal_dl_{task_id}_{idx_str}",
                    )

    # ── Scheduled slot (past or future) ───────────────────────────────────────
    elif kind == "scheduled" and len(parts) == 3:
        task_id      = parts[1]
        scheduled_iso = parts[2]
        task = tasks_by_id.get(task_id)
        if task is None:
            st.warning("Task no longer in session.")
        else:
            sched_dt = _parse_dt(scheduled_iso)
            is_future = sched_dt is not None and sched_dt >= now

            if is_future:
                st.subheader(f"🔵 Upcoming Run — {task['name']}")
            else:
                st.subheader(f"🟦 Scheduled Slot — {task['name']}")

            if sched_dt:
                st.caption(f"{'Scheduled' if is_future else 'Was scheduled'}: "
                           f"{sched_dt.strftime('%b %d, %Y at %H:%M UTC')}")
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

            st.markdown("**Sources:** " + (" · ".join(enabled_sources) if enabled_sources else "_(none enabled)_"))

            if not is_future:
                # Check if there's an actual output near this slot
                matching = [
                    (i, o) for i, o in enumerate(task.get("outputs", []))
                    if o.get("timestamp", "")[:10] == sched_dt.strftime("%Y-%m-%d")
                ]
                if matching:
                    idx, output = matching[0]
                    st.success(f"Draft recorded for this date — Run #{len(task['outputs']) - idx}")
                    with st.expander("Draft text", expanded=False):
                        st.markdown(output.get("text", "_(no text)_"))
                    if output.get("docx_bytes"):
                        date_str = sched_dt.strftime("%Y-%m-%d")
                        st.download_button(
                            label="⬇️ Download .docx",
                            data=output["docx_bytes"],
                            file_name=f"CoSN_{task['name'].replace(' ', '_')}_{date_str}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"cal_sdl_{task_id}_{idx}",
                        )
                else:
                    st.info("No output recorded for this scheduled slot.", icon="📭")
    else:
        st.info("Click an event to see details.", icon="👆")
