"""Scheduler fragment — polls every 15s, fires due tasks, syncs results."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from agent.runner import submit_task, poll_result, clear_result
from agent.task import schedule_next


@st.fragment(run_every=15)
def scheduler_fragment() -> None:
    """
    Runs every 15 seconds as a lightweight background loop.
    - Syncs completed task results back into session state.
    - Submits tasks whose next_run has passed.
    - Shows a one-line status caption.
    """
    api_config = st.session_state.get("api_config", {})
    tasks = st.session_state.get("tasks", [])
    now = datetime.now(timezone.utc)
    changed = False

    for task in tasks:
        # ── Sync completed results ────────────────────────────────────────────
        if task["status"] == "running":
            result = poll_result(task["id"])
            if result and result["status"] != "running":
                if result["status"] == "done":
                    task["status"] = "done"
                    task["last_run"] = now
                    schedule_next(task, now)
                    task["outputs"].insert(0, {
                        "timestamp":   result["timestamp"],
                        "text":        result["output"],
                        "docx_bytes":  result["docx_bytes"],
                        "model":       task["model"],
                        "sources_used": result.get("sources_used", []),
                    })
                    task["outputs"] = task["outputs"][:5]  # keep last 5
                else:
                    task["status"] = "error"
                    task["last_error"] = result.get("error", "Unknown error")
                    schedule_next(task, now)
                clear_result(task["id"])
                changed = True

        # ── Fire due tasks ────────────────────────────────────────────────────
        elif (
            task["enabled"]
            and task["status"] not in ("running",)
            and task.get("next_run") is not None
            and now >= task["next_run"]
        ):
            submit_task(task, api_config)
            task["status"] = "running"
            changed = True

    if changed:
        st.rerun()

    # ── Status line ───────────────────────────────────────────────────────────
    running = [t["name"] for t in tasks if t["status"] == "running"]
    upcoming = sorted(
        [t for t in tasks if t["enabled"] and t.get("next_run") and t["status"] != "running"],
        key=lambda t: t["next_run"],
    )

    if running:
        st.caption(f"🔄 Running: {', '.join(running)}")
    elif upcoming:
        secs = max(0, int((upcoming[0]["next_run"] - now).total_seconds()))
        m, s = divmod(secs, 60)
        countdown = f"{m}m {s:02d}s" if m else f"{s}s"
        st.caption(f"⏱ Next: **{upcoming[0]['name']}** in {countdown}")
    elif tasks:
        st.caption("○ All tasks idle or paused.")
