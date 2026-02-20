import streamlit as st

STRIPE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: Inter, sans-serif !important;
}

/* Page background */
.stApp {
    background-color: #FFFFFF;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #F6F9FC;
    border-right: 1px solid #E3E8EF;
    color: #0A2540 !important;
}
[data-testid="stSidebar"] * {
    color: #0A2540 !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCheckbox > label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stFileUploader label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: #0A2540 !important;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #0A2540 !important;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-top: 1.2rem;
    margin-bottom: 0.4rem;
}
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stSelectbox > div > div > div {
    color: #0A2540 !important;
    background: #FFFFFF !important;
}

/* Primary button — Stripe indigo */
.stButton > button[kind="primary"] {
    background: #635BFF !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    padding: 0.5rem 1.4rem !important;
    transition: background 0.15s ease !important;
}
.stButton > button[kind="primary"]:hover {
    background: #4B44CC !important;
}

/* Secondary button */
.stButton > button[kind="secondary"] {
    border: 1px solid #E3E8EF !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    color: #425466 !important;
    background: #FFFFFF !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #635BFF !important;
    color: #635BFF !important;
}

/* Download button */
.stDownloadButton > button {
    background: #635BFF !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.4rem !important;
}
.stDownloadButton > button:hover {
    background: #4B44CC !important;
}

/* Input fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {
    border: 1px solid #E3E8EF !important;
    border-radius: 6px !important;
    background: #F6F9FC !important;
    font-size: 0.875rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #635BFF !important;
    box-shadow: 0 0 0 3px rgba(99, 91, 255, 0.12) !important;
}

/* Slider */
.stSlider > div > div > div > div {
    background: #635BFF !important;
}

/* Toggle / checkbox */
.stCheckbox > label > span:first-child {
    border-color: #E3E8EF !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: #F6F9FC !important;
    border: 1px solid #E3E8EF !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    color: #0A2540 !important;
}

/* Cards */
.cos-card {
    border: 1px solid #E3E8EF;
    border-radius: 8px;
    padding: 20px 24px;
    background: #FFFFFF;
    margin-bottom: 16px;
}
.cos-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}
.cos-card-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #0A2540;
    margin: 0;
}
.cos-card-meta {
    font-size: 0.78rem;
    color: #6B7C93;
    margin-top: 2px;
}
.cos-source-card {
    border: 1px solid #E3E8EF;
    border-radius: 8px;
    padding: 16px 20px;
    background: #FFFFFF;
    height: 100%;
    transition: border-color 0.15s ease;
}
.cos-source-card.active {
    border-color: #635BFF;
    background: #FAFAFE;
}
.cos-source-icon {
    font-size: 1.4rem;
    margin-bottom: 8px;
    display: block;
}
.cos-source-name {
    font-size: 0.88rem;
    font-weight: 600;
    color: #0A2540;
}
.cos-source-status {
    font-size: 0.75rem;
    color: #6B7C93;
    margin-top: 4px;
}

/* Status badges */
.badge-success {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #09825D;
    font-weight: 600;
    font-size: 0.78rem;
    background: #ECFDF5;
    padding: 2px 8px;
    border-radius: 20px;
}
.badge-error {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #C0392B;
    font-weight: 600;
    font-size: 0.78rem;
    background: #FEF2F2;
    padding: 2px 8px;
    border-radius: 20px;
}
.badge-idle {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #6B7C93;
    font-weight: 600;
    font-size: 0.78rem;
    background: #F6F9FC;
    padding: 2px 8px;
    border-radius: 20px;
}
.badge-running {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #635BFF;
    font-weight: 600;
    font-size: 0.78rem;
    background: #F0EFFF;
    padding: 2px 8px;
    border-radius: 20px;
}

/* Step indicator */
.step-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    font-weight: 500;
}
.step-active {
    color: #635BFF;
    font-weight: 600;
}
.step-done {
    color: #09825D;
}
.step-idle {
    color: #6B7C93;
}
.step-error {
    color: #C0392B;
}
.step-divider {
    color: #E3E8EF;
    font-size: 1rem;
}

/* Page header */
.cos-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 16px;
    border-bottom: 1px solid #E3E8EF;
    margin-bottom: 28px;
}
.cos-wordmark {
    font-size: 1.35rem;
    font-weight: 700;
    color: #0A2540;
    letter-spacing: -0.02em;
}
.cos-wordmark span {
    color: #635BFF;
}
.cos-subtitle {
    font-size: 0.82rem;
    color: #6B7C93;
    margin-top: 2px;
}

/* Section heading */
.cos-section-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6B7C93;
    margin-bottom: 12px;
}

/* Divider */
.cos-divider {
    border: none;
    border-top: 1px solid #E3E8EF;
    margin: 24px 0;
}

/* File chip */
.cos-file-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #F6F9FC;
    border: 1px solid #E3E8EF;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.8rem;
    color: #425466;
    margin-right: 6px;
    margin-bottom: 6px;
}

/* Run bar */
.cos-run-bar {
    background: #F6F9FC;
    border: 1px solid #E3E8EF;
    border-radius: 8px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin: 24px 0;
}

/* Info boxes */
.cos-info {
    background: #F0EFFF;
    border: 1px solid #D4D2FF;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.82rem;
    color: #425466;
    margin-bottom: 12px;
}

/* Scrollable preview */
.cos-preview {
    background: #F6F9FC;
    border: 1px solid #E3E8EF;
    border-radius: 8px;
    padding: 20px 24px;
    max-height: 480px;
    overflow-y: auto;
    font-size: 0.875rem;
    line-height: 1.7;
    color: #425466;
    white-space: pre-wrap;
}

/* Hide Streamlit default elements */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""


def inject_styles() -> None:
    st.markdown(STRIPE_CSS, unsafe_allow_html=True)
