"""
CoSN Agent Orchestration Dashboard — Main page.
Streamlit POC v0.2 | February 2026
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(
    page_title="CoSN Agent Dashboard",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="expanded",
)

from ui.styles import inject_styles
from ui.components import render_step_indicator
from agent.sources.luma import fetch_luma_events, normalize_luma
from agent.sources.spotify import fetch_spotify_episodes, normalize_spotify
from agent.sources.webflow import fetch_webflow_jobs, normalize_webflow_jobs
from agent.files import extract_all, extract_text
from agent.context import assemble_context
from agent.claude import stream_generation, AVAILABLE_MODELS
from agent.output import generate_docx

inject_styles()

# ── Session state ─────────────────────────────────────────────────────────────
_DEFAULTS = {
    "run_status": "idle",
    "last_output": "",
    "last_docx": None,
    "last_model": AVAILABLE_MODELS[0],
    "run_history": [],
    "run_error": "",
    "source_status": {"luma": "idle", "spotify": "idle", "webflow": "idle"},
    "normalized": {"luma": "", "spotify": "", "webflow": ""},
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _env_or_session(env_var: str, session_key: str, sidebar_val: str) -> str:
    if sidebar_val.strip():
        return sidebar_val.strip()
    cfg = st.session_state.get(session_key, "")
    if cfg:
        return cfg
    try:
        return st.secrets.get(env_var, os.getenv(env_var, ""))
    except Exception:
        return os.getenv(env_var, "")


def _run_async(coro):
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("API Keys")
    st.caption("Keys set in .env are loaded automatically.")
    sb_anthropic      = st.text_input("Anthropic Key", type="password", placeholder="sk-ant-…")
    sb_luma           = st.text_input("Luma API Key", type="password")
    sb_spotify_id     = st.text_input("Spotify Client ID", type="password")
    sb_spotify_secret = st.text_input("Spotify Client Secret", type="password")
    sb_webflow        = st.text_input("Webflow API Key", type="password")
    sb_webflow_collection = st.text_input("Webflow Collection ID")
    sb_webflow_domain     = st.text_input("Webflow Site Domain", placeholder="e.g. cosn.community")

    st.divider()
    st.header("Model")
    selected_model = st.selectbox("Claude model", AVAILABLE_MODELS)

    st.divider()
    st.header("Sources")
    luma_enabled    = st.checkbox("📅 Luma Events", value=True)
    luma_days       = st.slider("Look-ahead (days)", 7, 60, 21) if luma_enabled else 21
    spotify_enabled = st.checkbox("🎙️ Spotify Podcast", value=True)
    spotify_days    = st.slider("Look-back (days)", 1, 30, 7) if spotify_enabled else 7
    webflow_enabled = st.checkbox("💼 Webflow Jobs", value=True)

    st.divider()
    st.header("Template & Context")
    template_file  = st.file_uploader("Newsletter template", type=["docx", "txt", "md"])
    context_files  = st.file_uploader("Additional context docs", type=["docx", "txt", "md"], accept_multiple_files=True)


# ── Resolve keys ──────────────────────────────────────────────────────────────
anthropic_key      = _env_or_session("ANTHROPIC_API_KEY",      "cfg_anthropic_key",      sb_anthropic)
luma_key           = _env_or_session("LUMA_API_KEY",           "cfg_luma_key",           sb_luma)
spotify_id         = _env_or_session("SPOTIFY_CLIENT_ID",      "cfg_spotify_id",         sb_spotify_id)
spotify_secret     = _env_or_session("SPOTIFY_CLIENT_SECRET",  "cfg_spotify_secret",     sb_spotify_secret)
webflow_key        = _env_or_session("WEBFLOW_API_KEY",        "cfg_webflow_key",        sb_webflow)
webflow_collection = _env_or_session("WEBFLOW_COLLECTION_ID",  "cfg_webflow_collection", sb_webflow_collection)
webflow_domain     = _env_or_session("WEBFLOW_SITE_DOMAIN",    "cfg_webflow_domain",     sb_webflow_domain)


# ── Header ────────────────────────────────────────────────────────────────────
st.title("CoSN Agent Dashboard")
st.caption("Newsletter Automation · " + {
    "idle": "⬜ Ready",
    "fetching": "🔄 Fetching data…",
    "generating": "🔄 Generating…",
    "done": "✅ Done",
    "error": "❌ Error",
}.get(st.session_state["run_status"], "⬜ Ready"))

st.divider()

# ── Source status ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
ss = st.session_state["source_status"]
status_icon = {"ok": "✅", "error": "❌", "idle": "○", "disabled": "—"}

with col1:
    s = ss["luma"] if luma_enabled else "disabled"
    st.metric("📅 Luma Events", f"{status_icon.get(s, '○')} {s.title()}")
with col2:
    s = ss["spotify"] if spotify_enabled else "disabled"
    st.metric("🎙️ Spotify", f"{status_icon.get(s, '○')} {s.title()}")
with col3:
    s = ss["webflow"] if webflow_enabled else "disabled"
    st.metric("💼 Webflow Jobs", f"{status_icon.get(s, '○')} {s.title()}")

st.divider()

# ── Uploaded files ────────────────────────────────────────────────────────────
all_uploads = ([template_file] if template_file else []) + (context_files or [])
if all_uploads:
    st.caption("Uploaded: " + "  ·  ".join(f"📄 {f.name}" for f in all_uploads))
    with st.expander("Preview uploaded files"):
        for fname, text in extract_all(all_uploads).items():
            st.markdown(f"**{fname}**")
            st.code(text[:1500] + ("…" if len(text) > 1500 else ""), language=None)

# ── Run bar ───────────────────────────────────────────────────────────────────
run_col, step_col = st.columns([1, 2])
with run_col:
    run_clicked = st.button("▶ Run Automation", type="primary", use_container_width=True)
with step_col:
    render_step_indicator(st.session_state["run_status"])

# ── Validation ────────────────────────────────────────────────────────────────
if run_clicked:
    errors = []
    if not anthropic_key:
        errors.append("Anthropic API key is required.")
    if luma_enabled and not luma_key:
        errors.append("Luma API key is required (or disable Luma).")
    if spotify_enabled and (not spotify_id or not spotify_secret):
        errors.append("Spotify Client ID + Secret required (or disable Spotify).")
    if webflow_enabled and not webflow_key:
        errors.append("Webflow API key is required (or disable Webflow).")
    for e in errors:
        st.error(e)
    if errors:
        run_clicked = False

# ── Run automation ────────────────────────────────────────────────────────────
if run_clicked:
    st.session_state.update({
        "run_status": "fetching",
        "run_error": "",
        "last_output": "",
        "last_docx": None,
        "source_status": {"luma": "idle", "spotify": "idle", "webflow": "idle"},
        "normalized": {"luma": "", "spotify": "", "webflow": ""},
    })

    # 1. Fetch
    async def _fetch_all():
        tasks = {}
        if luma_enabled:    tasks["luma"]    = fetch_luma_events(luma_key, luma_days)
        if spotify_enabled: tasks["spotify"] = fetch_spotify_episodes(spotify_id, spotify_secret, spotify_days)
        if webflow_enabled: tasks["webflow"] = fetch_webflow_jobs(webflow_key, webflow_collection, webflow_domain)
        if not tasks:
            return {}
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return dict(zip(tasks.keys(), gathered))

    with st.spinner("Fetching data from sources…"):
        try:
            raw = _run_async(_fetch_all())
        except Exception as exc:
            st.session_state["run_status"] = "error"
            st.session_state["run_error"] = str(exc)
            raw = {}

    # 2. Normalize
    luma_text = spotify_text = webflow_text = ""

    if "luma" in raw:
        r = raw["luma"]
        if isinstance(r, Exception):
            st.session_state["source_status"]["luma"] = "error"
            st.warning(f"Luma: {r}")
        else:
            st.session_state["source_status"]["luma"] = "ok"
            luma_text = normalize_luma(r, luma_days)
            st.session_state["normalized"]["luma"] = luma_text

    if "spotify" in raw:
        r = raw["spotify"]
        if isinstance(r, Exception):
            st.session_state["source_status"]["spotify"] = "error"
            st.warning(f"Spotify: {r}")
        else:
            st.session_state["source_status"]["spotify"] = "ok"
            spotify_text = normalize_spotify(r, spotify_days)
            st.session_state["normalized"]["spotify"] = spotify_text

    if "webflow" in raw:
        r = raw["webflow"]
        if isinstance(r, Exception):
            st.session_state["source_status"]["webflow"] = "error"
            st.warning(f"Webflow: {r}")
        else:
            jobs, domain = r
            st.session_state["source_status"]["webflow"] = "ok"
            webflow_text = normalize_webflow_jobs(jobs, domain)
            st.session_state["normalized"]["webflow"] = webflow_text

    # 3. Extract files
    template_text = ""
    uploaded_docs = {}
    if template_file:
        try:
            template_text = extract_text(template_file)
        except Exception as exc:
            st.warning(f"Could not read template: {exc}")
    if context_files:
        try:
            uploaded_docs = extract_all(context_files)
        except Exception as exc:
            st.warning(f"Could not read context files: {exc}")

    # 4. Assemble context
    full_context = assemble_context(
        luma_text=luma_text,
        spotify_text=spotify_text,
        webflow_text=webflow_text,
        uploaded_docs=uploaded_docs or None,
        template_text=template_text,
    )

    # 5. Stream generation
    st.session_state["run_status"] = "generating"
    st.divider()
    st.subheader("Generated Newsletter Draft")
    placeholder = st.empty()
    full_text = ""

    try:
        for chunk in stream_generation(anthropic_key, full_context, model=selected_model):
            full_text += chunk
            placeholder.markdown(full_text + "▌")
        placeholder.markdown(full_text)
        st.session_state["last_output"] = full_text
        st.session_state["last_model"] = selected_model
        st.session_state["run_status"] = "done"
    except Exception as exc:
        st.session_state["run_status"] = "error"
        st.session_state["run_error"] = str(exc)
        st.error(f"Generation failed: {exc}")
        full_text = ""

    # 6. Generate docx
    if full_text:
        try:
            st.session_state["last_docx"] = generate_docx(full_text, selected_model)
        except Exception as exc:
            st.warning(f"Could not generate .docx: {exc}")

    # 7. Record history
    st.session_state["run_history"].append({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "model": selected_model,
        "status": st.session_state["run_status"],
        "sources": [s for s, en in [("Luma", luma_enabled), ("Spotify", spotify_enabled), ("Webflow Jobs", webflow_enabled)] if en],
        "error": st.session_state.get("run_error", ""),
        "output": full_text,
    })

    st.rerun()

# ── Output ────────────────────────────────────────────────────────────────────
if st.session_state["last_output"]:
    st.divider()
    st.subheader("Generated Newsletter Draft")

    with st.expander("View output", expanded=True):
        st.markdown(st.session_state["last_output"])

    with st.expander("View raw source data"):
        norm = st.session_state["normalized"]
        for label, key in [("Luma Events", "luma"), ("Spotify", "spotify"), ("Webflow Jobs", "webflow")]:
            if norm[key]:
                st.markdown(f"**{label}**")
                st.code(norm[key], language=None)

    st.divider()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dl_col, reset_col = st.columns([2, 1])
    with dl_col:
        if st.session_state["last_docx"]:
            st.download_button(
                label="⬇️ Download Newsletter (.docx)",
                data=st.session_state["last_docx"],
                file_name=f"CoSN_Newsletter_{date_str}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
            )
    with reset_col:
        if st.button("Reset", type="secondary"):
            for key in ["run_status", "last_output", "last_docx", "run_error", "normalized", "source_status"]:
                st.session_state[key] = _DEFAULTS.get(key, "")
            st.rerun()

elif st.session_state["run_status"] == "error":
    st.error(f"Run failed: {st.session_state['run_error']}")
    if st.button("Reset"):
        st.session_state["run_status"] = "idle"
        st.session_state["run_error"] = ""
        st.rerun()

else:
    st.divider()
    st.info(
        "**Ready to generate.**\n\n"
        "1. API keys are loaded from `.env` automatically\n"
        "2. Toggle sources and adjust date windows in the sidebar\n"
        "3. Optionally upload a newsletter template\n"
        "4. Click **▶ Run Automation**\n"
        "5. Download the finished `.docx`",
        icon="🚀",
    )
