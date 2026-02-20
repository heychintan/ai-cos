"""
CoSN Agent Orchestration Dashboard — Main page (Dashboard).
Streamlit POC v0.2 | February 2026
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import streamlit as st

# ── Load .env for local dev ───────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="CoSN Agent Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Internal imports ──────────────────────────────────────────────────────────
from ui.styles import inject_styles
from ui.components import (
    render_header,
    render_source_card,
    render_step_indicator,
    section_label,
    cos_divider,
    info_box,
    file_chips,
)
from agent.sources.luma import fetch_luma_events, normalize_luma
from agent.sources.spotify import fetch_spotify_episodes, normalize_spotify
from agent.sources.webflow import fetch_webflow_jobs, normalize_webflow_jobs
from agent.files import extract_all
from agent.context import assemble_context
from agent.claude import stream_generation, AVAILABLE_MODELS
from agent.output import generate_docx

inject_styles()

# ── Session state defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "run_status": "idle",       # idle | fetching | generating | done | error
    "last_output": "",
    "last_docx": None,
    "last_model": "claude-sonnet-4-6",
    "run_history": [],
    "run_error": "",
    "source_status": {          # per-source fetch status
        "luma": "idle",
        "spotify": "idle",
        "webflow": "idle",
    },
    "normalized": {             # normalized text per source
        "luma": "",
        "spotify": "",
        "webflow": "",
    },
    "webflow_site_domain": "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ───────────────────────────────────────────────────────────────────

def _env_or_session(env_var: str, session_key: str, sidebar_val: str) -> str:
    """
    Key resolution priority:
      1. Non-empty sidebar override entered this session
      2. Config page session value
      3. Environment variable / st.secrets
    """
    if sidebar_val.strip():
        return sidebar_val.strip()
    cfg_val = st.session_state.get(session_key, "")
    if cfg_val:
        return cfg_val
    try:
        return st.secrets.get(env_var, os.getenv(env_var, ""))
    except Exception:
        return os.getenv(env_var, "")


def _run_async(coro):
    """Run an async coroutine safely from a Streamlit thread."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 API Keys")
    info_box("Keys are never stored — session only. Set <code>.env</code> for persistence.")

    sb_anthropic = st.text_input("Anthropic Key", type="password", placeholder="sk-ant-…")
    sb_luma = st.text_input("Luma API Key", type="password", placeholder="luma-…")
    sb_spotify_id = st.text_input("Spotify Client ID", type="password")
    sb_spotify_secret = st.text_input("Spotify Client Secret", type="password")
    sb_webflow = st.text_input("Webflow API Key", type="password")
    sb_webflow_collection = st.text_input(
        "Webflow Collection ID",
        placeholder="Optional — auto-discovers if blank",
    )

    st.markdown("### ⚡ Model")
    cfg_model = st.session_state.get("cfg_model", AVAILABLE_MODELS[0])
    model_idx = AVAILABLE_MODELS.index(cfg_model) if cfg_model in AVAILABLE_MODELS else 0
    selected_model = st.selectbox("Claude model", AVAILABLE_MODELS, index=model_idx)

    st.markdown("### 📡 Sources")
    luma_enabled = st.checkbox("Luma Events", value=True)
    if luma_enabled:
        luma_days = st.slider("Look-ahead (days)", 7, 60, 21, key="luma_days")
    else:
        luma_days = 21

    spotify_enabled = st.checkbox("Spotify Podcast", value=True)
    if spotify_enabled:
        spotify_days = st.slider("Look-back (days)", 1, 30, 7, key="spotify_days")
    else:
        spotify_days = 7

    webflow_enabled = st.checkbox("Webflow Jobs", value=True)

    st.markdown("### 📄 Template & Context")
    template_file = st.file_uploader(
        "Newsletter template",
        type=["docx", "txt", "md"],
        help="Upload your newsletter template. Claude will follow its structure exactly.",
    )
    context_files = st.file_uploader(
        "Additional context docs",
        type=["docx", "txt", "md"],
        accept_multiple_files=True,
        help="Optional extra docs (style guide, previous issues, etc.).",
    )

# ── Resolve keys ──────────────────────────────────────────────────────────────
anthropic_key = _env_or_session("ANTHROPIC_API_KEY", "cfg_anthropic_key", sb_anthropic)
luma_key = _env_or_session("LUMA_API_KEY", "cfg_luma_key", sb_luma)
spotify_id = _env_or_session("SPOTIFY_CLIENT_ID", "cfg_spotify_id", sb_spotify_id)
spotify_secret = _env_or_session("SPOTIFY_CLIENT_SECRET", "cfg_spotify_secret", sb_spotify_secret)
webflow_key = _env_or_session("WEBFLOW_API_KEY", "cfg_webflow_key", sb_webflow)
webflow_collection = _env_or_session(
    "WEBFLOW_COLLECTION_ID", "cfg_webflow_collection", sb_webflow_collection
)

# ── Header ────────────────────────────────────────────────────────────────────
render_header(st.session_state["run_status"])

# ── Source cards ──────────────────────────────────────────────────────────────
section_label("Data Sources")
col_luma, col_spotify, col_webflow = st.columns(3)

with col_luma:
    luma_status = "idle" if luma_enabled else "disabled"
    if luma_enabled and st.session_state["source_status"]["luma"] != "idle":
        luma_status = st.session_state["source_status"]["luma"]
    render_source_card(
        icon="📅",
        name="Luma Events",
        description=f"Next {luma_days} days · cal-9Z75…",
        status=luma_status,
        enabled=luma_enabled,
    )

with col_spotify:
    sp_status = "idle" if spotify_enabled else "disabled"
    if spotify_enabled and st.session_state["source_status"]["spotify"] != "idle":
        sp_status = st.session_state["source_status"]["spotify"]
    render_source_card(
        icon="🎙️",
        name="Spotify Podcast",
        description=f"Last {spotify_days} days · CoSN show",
        status=sp_status,
        enabled=spotify_enabled,
    )

with col_webflow:
    wf_status = "idle" if webflow_enabled else "disabled"
    if webflow_enabled and st.session_state["source_status"]["webflow"] != "idle":
        wf_status = st.session_state["source_status"]["webflow"]
    render_source_card(
        icon="💼",
        name="Webflow Jobs",
        description="Published job postings · CMS",
        status=wf_status,
        enabled=webflow_enabled,
    )

cos_divider()

# ── Context docs preview ──────────────────────────────────────────────────────
section_label("Context Documents")

all_uploads = ([template_file] if template_file else []) + (context_files or [])
if all_uploads:
    file_chips(all_uploads)
    with st.expander("Preview uploaded files"):
        docs_map = extract_all(all_uploads)
        for fname, text in docs_map.items():
            st.markdown(f"**{fname}**")
            st.code(text[:1500] + ("…" if len(text) > 1500 else ""), language=None)
else:
    st.caption("No files uploaded. Add a template in the sidebar for best results.")

cos_divider()

# ── Run bar ───────────────────────────────────────────────────────────────────
section_label("Automation")

run_col, step_col = st.columns([1, 3])
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
        errors.append("Spotify Client ID + Secret are required (or disable Spotify).")
    if webflow_enabled and not webflow_key:
        errors.append("Webflow API key is required (or disable Webflow).")

    if errors:
        for e in errors:
            st.error(e)
        run_clicked = False

# ── Run automation ────────────────────────────────────────────────────────────
if run_clicked:
    st.session_state["run_status"] = "fetching"
    st.session_state["run_error"] = ""
    st.session_state["last_output"] = ""
    st.session_state["last_docx"] = None
    st.session_state["source_status"] = {"luma": "idle", "spotify": "idle", "webflow": "idle"}
    st.session_state["normalized"] = {"luma": "", "spotify": "", "webflow": ""}

    # ── 1. Fetch data sources ─────────────────────────────────────────────────
    async def _fetch_all():
        tasks = {}
        if luma_enabled:
            tasks["luma"] = fetch_luma_events(luma_key, luma_days)
        if spotify_enabled:
            tasks["spotify"] = fetch_spotify_episodes(spotify_id, spotify_secret, spotify_days)
        if webflow_enabled:
            tasks["webflow"] = fetch_webflow_jobs(webflow_key, webflow_collection)

        results = {}
        if tasks:
            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), gathered):
                results[key] = result
        return results

    with st.spinner("Fetching data from sources…"):
        try:
            raw_results = _run_async(_fetch_all())
        except Exception as exc:
            st.session_state["run_status"] = "error"
            st.session_state["run_error"] = f"Fetch error: {exc}"
            raw_results = {}

    # ── 2. Normalize ──────────────────────────────────────────────────────────
    luma_text = ""
    spotify_text = ""
    webflow_text = ""

    if "luma" in raw_results:
        result = raw_results["luma"]
        if isinstance(result, Exception):
            st.session_state["source_status"]["luma"] = "error"
            st.warning(f"Luma fetch failed: {result}")
        else:
            st.session_state["source_status"]["luma"] = "ok"
            luma_text = normalize_luma(result, luma_days)
            st.session_state["normalized"]["luma"] = luma_text

    if "spotify" in raw_results:
        result = raw_results["spotify"]
        if isinstance(result, Exception):
            st.session_state["source_status"]["spotify"] = "error"
            st.warning(f"Spotify fetch failed: {result}")
        else:
            st.session_state["source_status"]["spotify"] = "ok"
            spotify_text = normalize_spotify(result, spotify_days)
            st.session_state["normalized"]["spotify"] = spotify_text

    if "webflow" in raw_results:
        result = raw_results["webflow"]
        if isinstance(result, Exception):
            st.session_state["source_status"]["webflow"] = "error"
            st.warning(f"Webflow fetch failed: {result}")
        else:
            jobs_list, site_domain = result
            st.session_state["source_status"]["webflow"] = "ok"
            st.session_state["webflow_site_domain"] = site_domain
            webflow_text = normalize_webflow_jobs(jobs_list, site_domain)
            st.session_state["normalized"]["webflow"] = webflow_text

    # ── 3. Extract uploaded files ─────────────────────────────────────────────
    template_text = ""
    uploaded_docs: dict[str, str] = {}

    if template_file:
        try:
            from agent.files import extract_text
            template_text = extract_text(template_file)
        except Exception as exc:
            st.warning(f"Could not read template: {exc}")

    if context_files:
        try:
            uploaded_docs = extract_all(context_files)
        except Exception as exc:
            st.warning(f"Could not read context files: {exc}")

    # ── 4. Assemble context ───────────────────────────────────────────────────
    full_context = assemble_context(
        luma_text=luma_text,
        spotify_text=spotify_text,
        webflow_text=webflow_text,
        uploaded_docs=uploaded_docs or None,
        template_text=template_text,
    )

    # ── 5. Stream Claude generation ───────────────────────────────────────────
    st.session_state["run_status"] = "generating"

    cos_divider()
    section_label("Generated Newsletter Draft")
    stream_placeholder = st.empty()
    full_text = ""

    try:
        for chunk in stream_generation(
            api_key=anthropic_key,
            context=full_context,
            model=selected_model,
            max_tokens=4096,
        ):
            full_text += chunk
            stream_placeholder.markdown(full_text + "▌")

        stream_placeholder.markdown(full_text)
        st.session_state["last_output"] = full_text
        st.session_state["last_model"] = selected_model
        st.session_state["run_status"] = "done"

    except Exception as exc:
        st.session_state["run_status"] = "error"
        st.session_state["run_error"] = str(exc)
        st.error(f"Generation failed: {exc}")
        full_text = ""

    # ── 6. Generate .docx ─────────────────────────────────────────────────────
    if full_text:
        try:
            docx_bytes = generate_docx(full_text, selected_model)
            st.session_state["last_docx"] = docx_bytes
        except Exception as exc:
            st.warning(f"Could not generate .docx: {exc}")

    # ── 7. Record history ─────────────────────────────────────────────────────
    active_sources = []
    if luma_enabled:
        active_sources.append("Luma")
    if spotify_enabled:
        active_sources.append("Spotify")
    if webflow_enabled:
        active_sources.append("Webflow Jobs")

    st.session_state["run_history"].append({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "model": selected_model,
        "status": st.session_state["run_status"],
        "sources": active_sources,
        "error": st.session_state.get("run_error", ""),
        "output": full_text,
    })

    st.rerun()

# ── Output area (shown after a successful run) ────────────────────────────────
if st.session_state["last_output"]:
    cos_divider()
    section_label("Generated Newsletter Draft")

    with st.expander("View full output", expanded=True):
        st.markdown(st.session_state["last_output"])

    # Normalized data preview
    with st.expander("View normalized source data"):
        norm = st.session_state["normalized"]
        if norm["luma"]:
            st.markdown("**Luma Events**")
            st.code(norm["luma"], language=None)
        if norm["spotify"]:
            st.markdown("**Spotify Podcast**")
            st.code(norm["spotify"], language=None)
        if norm["webflow"]:
            st.markdown("**Webflow Jobs**")
            st.code(norm["webflow"], language=None)

    cos_divider()
    section_label("Download")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dl_col, reset_col = st.columns([2, 1])

    with dl_col:
        if st.session_state["last_docx"]:
            st.download_button(
                label="⬇️  Download Newsletter (.docx)",
                data=st.session_state["last_docx"],
                file_name=f"CoSN_Newsletter_{date_str}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
            )
        else:
            st.warning("No .docx available — see errors above.")

    with reset_col:
        if st.button("Reset", type="secondary"):
            for key in ["run_status", "last_output", "last_docx", "run_error", "normalized", "source_status"]:
                st.session_state[key] = _DEFAULTS.get(key, "")
            st.rerun()

elif st.session_state["run_status"] == "error":
    st.error(
        f"Run failed: {st.session_state['run_error']}  \n"
        "Check your API keys and try again."
    )
    if st.button("Reset", type="secondary"):
        st.session_state["run_status"] = "idle"
        st.session_state["run_error"] = ""
        st.rerun()

else:
    # Idle state — show helpful info
    cos_divider()
    st.markdown(
        """
        <div class="cos-card">
            <div class="cos-card-header">
                <span style="font-size:1.5rem;">🚀</span>
                <div>
                    <div class="cos-card-title">Ready to generate</div>
                    <div class="cos-card-meta">Configure your sources in the sidebar, then click <strong>Run Automation</strong>.</div>
                </div>
            </div>
            <ol style="color:#425466; font-size:0.875rem; line-height:1.9; margin:0; padding-left:1.2rem;">
                <li>Enter your API keys in the sidebar (or set them in <code>.env</code>)</li>
                <li>Toggle the sources you want to include</li>
                <li>Upload your newsletter template and any context docs</li>
                <li>Click <strong>▶ Run Automation</strong> and watch the draft appear</li>
                <li>Download the finished <code>.docx</code></li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )
