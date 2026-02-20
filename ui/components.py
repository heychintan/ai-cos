"""Reusable UI components for the CoSN dashboard."""
import streamlit as st


def render_header(run_status: str = "idle") -> None:
    badge = {
        "idle": '<span class="badge-idle">● Idle</span>',
        "fetching": '<span class="badge-running">⟳ Fetching data…</span>',
        "generating": '<span class="badge-running">⟳ Generating…</span>',
        "done": '<span class="badge-success">✓ Done</span>',
        "error": '<span class="badge-error">✕ Error</span>',
    }.get(run_status, '<span class="badge-idle">● Idle</span>')

    st.markdown(
        f"""
        <div class="cos-header">
            <div>
                <div class="cos-wordmark">Co<span>S</span>N Agent</div>
                <div class="cos-subtitle">Newsletter Automation Dashboard</div>
            </div>
            <div>{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_card(
    icon: str,
    name: str,
    description: str,
    status: str,
    enabled: bool,
) -> None:
    active_class = "active" if enabled else ""
    status_html = {
        "ok": '<span class="badge-success">✓ Fetched</span>',
        "error": '<span class="badge-error">✕ Failed</span>',
        "idle": '<span class="badge-idle">● Not fetched</span>',
        "disabled": '<span class="badge-idle">— Disabled</span>',
    }.get(status, '<span class="badge-idle">● Not fetched</span>')

    st.markdown(
        f"""
        <div class="cos-source-card {active_class}">
            <span class="cos-source-icon">{icon}</span>
            <div class="cos-source-name">{name}</div>
            <div class="cos-source-status">{description}</div>
            <div style="margin-top:10px;">{status_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_indicator(run_status: str) -> None:
    steps = [
        ("fetching", "Fetch Data"),
        ("generating", "Generate"),
        ("done", "Done"),
    ]
    order = ["idle", "fetching", "generating", "done", "error"]
    current_idx = order.index(run_status) if run_status in order else 0

    parts = []
    for i, (step_key, label) in enumerate(steps):
        step_idx = order.index(step_key)
        if run_status == "error" and step_key == "generating":
            cls = "step-error"
            icon = "✕"
        elif current_idx > step_idx:
            cls = "step-done"
            icon = "✓"
        elif current_idx == step_idx:
            cls = "step-active"
            icon = "⟳"
        else:
            cls = "step-idle"
            icon = "○"
        parts.append(f'<span class="{cls}">{icon} {label}</span>')
        if i < len(steps) - 1:
            parts.append('<span class="step-divider">→</span>')

    st.markdown(
        f'<div class="step-row">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(
        f'<div class="cos-section-label">{text}</div>',
        unsafe_allow_html=True,
    )


def cos_divider() -> None:
    st.markdown('<hr class="cos-divider">', unsafe_allow_html=True)


def info_box(text: str) -> None:
    st.markdown(
        f'<div class="cos-info">{text}</div>',
        unsafe_allow_html=True,
    )


def file_chips(files: list) -> None:
    if not files:
        return
    chips = "".join(
        f'<span class="cos-file-chip">📄 {f.name}</span>' for f in files
    )
    st.markdown(chips, unsafe_allow_html=True)
