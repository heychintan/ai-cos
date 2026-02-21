"""⚙️ Configuration — API keys, source settings, and template management."""
import os
import streamlit as st
from ui.styles import inject_styles

st.set_page_config(page_title="Config — CoSN Agent", page_icon="⚙️", layout="centered")
inject_styles()

st.title("⚙️ Configuration")
st.caption("Manage API keys and source settings. Keys entered here are saved for this session only.")

st.divider()

# ── API Keys ──────────────────────────────────────────────────────────────────
st.subheader("API Keys")
st.info("Keys entered here are saved only for this browser session. For persistence, add them to your `.env` file.", icon="ℹ️")

col1, col2 = st.columns(2)
with col1:
    anthropic_key       = st.text_input("Anthropic API Key",      value=st.session_state.get("cfg_anthropic_key", ""), type="password", placeholder="sk-ant-…")
    luma_key            = st.text_input("Luma API Key",           value=st.session_state.get("cfg_luma_key", ""),      type="password")
    spotify_id          = st.text_input("Spotify Client ID",      value=st.session_state.get("cfg_spotify_id", ""),    type="password")
with col2:
    spotify_secret      = st.text_input("Spotify Client Secret",  value=st.session_state.get("cfg_spotify_secret", ""), type="password")
    webflow_key         = st.text_input("Webflow API Key",        value=st.session_state.get("cfg_webflow_key", ""),    type="password")
    webflow_collection  = st.text_input("Webflow Collection ID",  value=st.session_state.get("cfg_webflow_collection", ""))
    webflow_domain      = st.text_input("Webflow Site Domain",    value=st.session_state.get("cfg_webflow_domain", ""), placeholder="e.g. cosn.community")

if st.button("Save to Session", type="primary"):
    st.session_state.update({
        "cfg_anthropic_key": anthropic_key,
        "cfg_luma_key": luma_key,
        "cfg_spotify_id": spotify_id,
        "cfg_spotify_secret": spotify_secret,
        "cfg_webflow_key": webflow_key,
        "cfg_webflow_collection": webflow_collection,
        "cfg_webflow_domain": webflow_domain,
    })
    st.success("Keys saved. Switch to the Dashboard to run the automation.")

st.divider()

# ── Model ─────────────────────────────────────────────────────────────────────
st.subheader("Claude Model")
from agent.claude import AVAILABLE_MODELS
default_model = st.session_state.get("cfg_model", AVAILABLE_MODELS[0])
selected_model = st.selectbox("Default model", AVAILABLE_MODELS, index=AVAILABLE_MODELS.index(default_model) if default_model in AVAILABLE_MODELS else 0)
if st.button("Save Model"):
    st.session_state["cfg_model"] = selected_model
    st.success(f"Default model set to **{selected_model}**.")

st.divider()

# ── Environment Status ─────────────────────────────────────────────────────────
st.subheader("Environment Status")
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

env_vars = {
    "ANTHROPIC_API_KEY":    os.getenv("ANTHROPIC_API_KEY"),
    "LUMA_API_KEY":         os.getenv("LUMA_API_KEY"),
    "SPOTIFY_CLIENT_ID":    os.getenv("SPOTIFY_CLIENT_ID"),
    "SPOTIFY_CLIENT_SECRET":os.getenv("SPOTIFY_CLIENT_SECRET"),
    "WEBFLOW_API_KEY":      os.getenv("WEBFLOW_API_KEY"),
    "WEBFLOW_COLLECTION_ID":os.getenv("WEBFLOW_COLLECTION_ID"),
    "WEBFLOW_SITE_DOMAIN":  os.getenv("WEBFLOW_SITE_DOMAIN"),
}

rows = []
for var, val in env_vars.items():
    status  = "✅ Set"   if val else "— Not set"
    preview = f"`{val[:4]}…`" if val and len(val) > 4 else ("`set`" if val else "—")
    rows.append({"Variable": f"`{var}`", "Status": status, "Preview": preview})

st.table(rows)
