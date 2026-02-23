"""
CoSN Agent Orchestration Dashboard
Streamlit POC v0.3 — Agentic task orchestration with in-session scheduling
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(
    page_title="CoSN Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.styles import inject_styles
from agent.task import new_task, schedule_next, fmt_interval, fmt_dt, INTERVAL_PRESETS
from agent.runner import submit_task
from agent.claude import AVAILABLE_MODELS
from scheduler import scheduler_fragment

inject_styles()

# ── Session state ─────────────────────────────────────────────────────────────
if "tasks" not in st.session_state:
    st.session_state["tasks"] = []


def _env(var: str, session_key: str, sidebar_val: str = "") -> str:
    if sidebar_val.strip():
        return sidebar_val.strip()
    cfg = st.session_state.get(session_key, "")
    if cfg:
        return cfg
    try:
        return st.secrets.get(var, os.getenv(var, ""))
    except Exception:
        return os.getenv(var, "")


# ── Sidebar — API keys ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("API Keys")
    st.caption("Loaded from `.env` automatically.")
    sb_anthropic          = st.text_input("Anthropic Key",        type="password", placeholder="sk-ant-…")
    sb_luma               = st.text_input("Luma API Key",         type="password")
    sb_spotify_id         = st.text_input("Spotify Client ID",    type="password")
    sb_spotify_secret     = st.text_input("Spotify Client Secret",type="password")
    sb_webflow                 = st.text_input("Webflow API Key",            type="password")
    sb_webflow_jobs_collection = st.text_input("Webflow Jobs Collection ID")
    sb_webflow_blogs_collection= st.text_input("Webflow Blogs Collection ID")
    sb_webflow_domain          = st.text_input("Webflow Site Domain",        placeholder="e.g. cosn.community")

api_config = {
    "anthropic_key":           _env("ANTHROPIC_API_KEY",            "cfg_anthropic_key",            sb_anthropic),
    "luma_key":                _env("LUMA_API_KEY",                 "cfg_luma_key",                 sb_luma),
    "spotify_id":              _env("SPOTIFY_CLIENT_ID",            "cfg_spotify_id",               sb_spotify_id),
    "spotify_secret":          _env("SPOTIFY_CLIENT_SECRET",        "cfg_spotify_secret",           sb_spotify_secret),
    "webflow_key":             _env("WEBFLOW_API_KEY",              "cfg_webflow_key",              sb_webflow),
    "webflow_jobs_collection": _env("WEBFLOW_JOBS_COLLECTION_ID",   "cfg_webflow_jobs_collection",  sb_webflow_jobs_collection),
    "webflow_blogs_collection":_env("WEBFLOW_BLOGS_COLLECTION_ID",  "cfg_webflow_blogs_collection", sb_webflow_blogs_collection),
    "webflow_domain":          _env("WEBFLOW_SITE_DOMAIN",          "cfg_webflow_domain",           sb_webflow_domain),
}
# Always keep api_config fresh for the scheduler fragment
st.session_state["api_config"] = api_config


# ── New Task dialog ───────────────────────────────────────────────────────────
@st.dialog("New Task", width="large")
def create_task_dialog() -> None:
    name         = st.text_input("Task name *", placeholder="Weekly LinkedIn Post, Slack Announcement…")
    instructions = st.text_area(
        "Instructions",
        placeholder="e.g. Focus on SF and NYC events. Lead with the podcast episode. Keep job listings concise.",
        height=90,
    )

    st.divider()
    col_src, col_sched = st.columns(2)

    with col_src:
        st.markdown("**Sources**")
        luma_en   = st.checkbox("📅 Luma Events",       value=True)
        luma_days = st.slider("Look-ahead (days)", 7, 60, 21, key="d_luma") if luma_en else 21
        sp_en     = st.checkbox("🎙️ Spotify Podcast",  value=True)
        sp_days   = st.slider("Look-back (days)", 1, 30, 7, key="d_spot") if sp_en else 7
        wf_en     = st.checkbox("💼 Webflow Jobs",      value=True)
        wf_blog_en= st.checkbox("📰 Webflow Blogs",     value=False)

    with col_sched:
        st.markdown("**Schedule & Model**")
        preset = st.selectbox("Repeat interval", list(INTERVAL_PRESETS.keys()) + ["Custom"])
        if preset == "Custom":
            interval = st.number_input("Seconds (min 60)", min_value=60, value=3600, step=60)
        else:
            interval = INTERVAL_PRESETS[preset]
        st.caption(f"Repeats every **{fmt_interval(int(interval))}**")
        model    = st.selectbox("Claude model", AVAILABLE_MODELS)
        run_now  = st.checkbox("Run immediately on create", value=True)

    st.divider()
    st.markdown("**Files**")
    tmpl      = st.file_uploader("Content template", type=["docx", "txt", "md"])
    ctx_files = st.file_uploader("Context docs", type=["docx", "txt", "md"], accept_multiple_files=True)

    st.write("")
    if st.button("Create Task", type="primary", use_container_width=True):
        if not name.strip():
            st.error("Task name is required.")
            return

        template  = {"name": tmpl.name,  "bytes": tmpl.read()}  if tmpl       else None
        docs      = [{"name": f.name,    "bytes": f.read()}      for f in (ctx_files or [])]

        task = new_task(
            name=name.strip(),
            instructions=instructions,
            interval=int(interval),
            model=model,
            luma_enabled=luma_en,
            luma_days=luma_days,
            spotify_enabled=sp_en,
            spotify_days=sp_days,
            webflow_enabled=wf_en,
            webflow_blogs_enabled=wf_blog_en,
            template=template,
            context_docs=docs,
        )

        if run_now:
            submit_task(task, api_config)
            task["status"] = "running"

        schedule_next(task)
        st.session_state["tasks"].append(task)
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("⚡ CoSN Agent Orchestration")
with col_btn:
    st.write("")
    if st.button("＋ New Task", type="primary", use_container_width=True):
        create_task_dialog()

# Scheduler fragment — auto-polls every 15s
scheduler_fragment()

st.divider()

# ── Task table ────────────────────────────────────────────────────────────────
tasks = st.session_state["tasks"]

if not tasks:
    st.info(
        "No tasks yet. Click **＋ New Task** to create your first automation.\n\n"
        "Each task pulls live data from your selected sources, generates content "
        "draft via Claude, and repeats on your chosen schedule — all within this session.",
        icon="⚡",
    )
else:
    st.subheader(f"Tasks ({len(tasks)})")

    # Column headers
    h = st.columns([2.5, 1.8, 1, 1.5, 1.5, 1.2, 1.8])
    for col, label in zip(h, ["Task", "Sources", "Every", "Last run", "Next run", "Status", "Actions"]):
        col.markdown(f"**{label}**")
    st.divider()

    for task in tasks:
        src_icons = "  ".join([
            icon for flag, icon in [
                (task["sources"]["luma"]["enabled"],                          "📅"),
                (task["sources"]["spotify"]["enabled"],                       "🎙️"),
                (task["sources"]["webflow"]["enabled"],                       "💼"),
                (task["sources"].get("webflow_blogs", {}).get("enabled"),     "📰"),
            ] if flag
        ]) or "—"

        status_display = {
            "idle":    "○ Idle",
            "running": "🔄 Running",
            "done":    "✅ Done",
            "error":   "❌ Error",
        }.get(task["status"], "—")

        next_run_display = fmt_dt(task.get("next_run")) if task["enabled"] else "Paused"

        row = st.columns([2.5, 1.8, 1, 1.5, 1.5, 1.2, 1.8])
        if row[0].button(f"**{task['name']}**", key=f"detail_{task['id']}", use_container_width=True):
            st.session_state["detail_task_id"] = task["id"]
            st.switch_page("pages/4_task.py")
        row[1].write(src_icons)
        row[2].write(fmt_interval(task["interval"]))
        row[3].write(fmt_dt(task.get("last_run")))
        row[4].write(next_run_display)
        row[5].write(status_display)

        with row[6]:
            a1, a2, a3 = st.columns(3)

            if a1.button("▶", key=f"run_{task['id']}", help="Run now",
                         disabled=(task["status"] == "running")):
                submit_task(task, api_config)
                task["status"] = "running"
                schedule_next(task)
                st.rerun()

            pause_label = "⏸" if task["enabled"] else "▷"
            pause_help  = "Pause" if task["enabled"] else "Resume"
            if a2.button(pause_label, key=f"pause_{task['id']}", help=pause_help):
                task["enabled"] = not task["enabled"]
                if task["enabled"]:
                    schedule_next(task)
                st.rerun()

            if a3.button("🗑", key=f"del_{task['id']}", help="Delete task"):
                st.session_state["tasks"] = [t for t in tasks if t["id"] != task["id"]]
                st.rerun()

        if task["status"] == "error" and task["last_error"]:
            st.error(f"↳ **{task['name']}**: {task['last_error']}")

    st.divider()

    # ── Outputs ───────────────────────────────────────────────────────────────
    tasks_with_output = [t for t in tasks if t.get("outputs")]
    if tasks_with_output:
        st.subheader("Outputs")
        for task in tasks_with_output:
            latest = task["outputs"][0]
            with st.expander(
                f"**{task['name']}** — {len(task['outputs'])} run(s) · latest {latest['timestamp']}",
                expanded=True,
            ):
                tab_labels = [f"Run {i+1} · {o['timestamp']}" for i, o in enumerate(task["outputs"])]
                tabs = st.tabs(tab_labels)

                for tab, output in zip(tabs, task["outputs"]):
                    with tab:
                        if output.get("sources_used"):
                            st.caption("Sources: " + " · ".join(output["sources_used"]))
                        st.markdown(output["text"])
                        if output.get("docx_bytes"):
                            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                            st.download_button(
                                label="⬇️ Download .docx",
                                data=output["docx_bytes"],
                                file_name=f"CoSN_{task['name'].replace(' ', '_')}_{date_str}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_{task['id']}_{output['timestamp']}",
                            )
