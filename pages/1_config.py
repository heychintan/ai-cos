"""
⚙️ Configuration — API keys, source settings, and template management.
This page is informational for the POC; keys are set in .env / st.secrets
or overridden in the sidebar on the Dashboard page.
"""
import streamlit as st
from ui.styles import inject_styles
from ui.components import section_label, cos_divider, info_box

st.set_page_config(
    page_title="Config — CoSN Agent",
    page_icon="⚙️",
    layout="wide",
)
inject_styles()

st.markdown("## ⚙️ Configuration")
st.markdown(
    "Manage API keys, source parameters, and template defaults. "
    "For the POC, keys can be set here via session state or stored in your `.env` / `st.secrets`."
)
cos_divider()

# ── API Keys ──────────────────────────────────────────────────────────────────
section_label("API Keys")
info_box(
    "Keys entered here are saved only for this browser session. "
    "For persistent config, add them to your <code>.env</code> file or Streamlit Cloud Secrets."
)

col1, col2 = st.columns(2)
with col1:
    anthropic_key = st.text_input(
        "Anthropic API Key",
        value=st.session_state.get("cfg_anthropic_key", ""),
        type="password",
        placeholder="sk-ant-...",
    )
    luma_key = st.text_input(
        "Luma API Key",
        value=st.session_state.get("cfg_luma_key", ""),
        type="password",
        placeholder="luma-...",
    )
    spotify_id = st.text_input(
        "Spotify Client ID",
        value=st.session_state.get("cfg_spotify_id", ""),
        type="password",
    )

with col2:
    spotify_secret = st.text_input(
        "Spotify Client Secret",
        value=st.session_state.get("cfg_spotify_secret", ""),
        type="password",
    )
    webflow_key = st.text_input(
        "Webflow API Key",
        value=st.session_state.get("cfg_webflow_key", ""),
        type="password",
    )
    webflow_collection = st.text_input(
        "Webflow Jobs Collection ID (optional)",
        value=st.session_state.get("cfg_webflow_collection", ""),
        placeholder="Leave blank to auto-discover",
    )

if st.button("Save to Session", type="primary"):
    st.session_state["cfg_anthropic_key"] = anthropic_key
    st.session_state["cfg_luma_key"] = luma_key
    st.session_state["cfg_spotify_id"] = spotify_id
    st.session_state["cfg_spotify_secret"] = spotify_secret
    st.session_state["cfg_webflow_key"] = webflow_key
    st.session_state["cfg_webflow_collection"] = webflow_collection
    st.success("Keys saved to session state. Switch to the Dashboard to run the automation.")

cos_divider()

# ── Source Defaults ────────────────────────────────────────────────────────────
section_label("Source Defaults")

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("**Luma Events**")
    luma_days = st.slider("Look-ahead window (days)", 7, 60, 21, key="cfg_luma_days")
    st.caption(f"Fetches events in the next **{luma_days} days** from `cal-9Z75SHNwmRJPyWb`.")

with col_b:
    st.markdown("**Spotify Podcast**")
    spotify_days = st.slider("Look-back window (days)", 1, 30, 7, key="cfg_spotify_days")
    st.caption(f"Fetches episodes released in the last **{spotify_days} days** from show `0mroNmOfEqWdkPEYYtN3PF`.")

with col_c:
    st.markdown("**Webflow Jobs**")
    st.caption(
        "Fetches all published, non-archived items from the Jobs collection. "
        "Set the Collection ID above to target a specific collection."
    )

cos_divider()

# ── Model ─────────────────────────────────────────────────────────────────────
section_label("Claude Model")
from agent.claude import AVAILABLE_MODELS
default_model = st.session_state.get("cfg_model", AVAILABLE_MODELS[0])
selected_model = st.selectbox(
    "Default model",
    AVAILABLE_MODELS,
    index=AVAILABLE_MODELS.index(default_model) if default_model in AVAILABLE_MODELS else 0,
)
if st.button("Save Model Preference"):
    st.session_state["cfg_model"] = selected_model
    st.success(f"Default model set to **{selected_model}**.")

cos_divider()

# ── Environment Status ────────────────────────────────────────────────────────
section_label("Environment Status")

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

env_vars = {
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    "LUMA_API_KEY": os.getenv("LUMA_API_KEY"),
    "SPOTIFY_CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID"),
    "SPOTIFY_CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET"),
    "WEBFLOW_API_KEY": os.getenv("WEBFLOW_API_KEY"),
    "WEBFLOW_COLLECTION_ID": os.getenv("WEBFLOW_COLLECTION_ID"),
}

rows = []
for var, val in env_vars.items():
    if val:
        status = f'<span class="badge-success">✓ Set</span>'
        preview = f"`{val[:4]}…`" if len(val) > 4 else "`set`"
    else:
        status = f'<span class="badge-idle">— Not set</span>'
        preview = "—"
    rows.append(f"| `{var}` | {status} | {preview} |")

table = "\n".join([
    "| Variable | Status | Preview |",
    "|---|---|---|",
] + rows)

st.markdown(table + "\n", unsafe_allow_html=True)
