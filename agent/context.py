"""Assemble the full Claude context string from all sources."""
from __future__ import annotations

from typing import Dict, Optional

TASK_INSTRUCTION = """\
Using the data above and following the template exactly, generate the \
newsletter draft. Output should be ready to copy into the final document \
with no further editing needed.\
"""


def assemble_context(
    luma_text: str = "",
    spotify_text: str = "",
    webflow_text: str = "",
    uploaded_docs: Optional[Dict[str, str]] = None,
    template_text: str = "",
) -> str:
    """
    Build the full prompt context string per PRD §6.2.
    """
    parts: list[str] = []

    # Data context block
    data_sections: list[str] = []
    if luma_text.strip():
        data_sections.append(luma_text.strip())
    if spotify_text.strip():
        data_sections.append(spotify_text.strip())
    if webflow_text.strip():
        data_sections.append(webflow_text.strip())

    if data_sections:
        parts.append("=== DATA CONTEXT ===")
        parts.append("\n\n".join(data_sections))
    else:
        parts.append("=== DATA CONTEXT ===")
        parts.append("(No live data fetched — work from uploaded documents and template only.)")

    # Uploaded documents block
    parts.append("\n=== UPLOADED DOCUMENTS ===")
    if uploaded_docs:
        for filename, text in uploaded_docs.items():
            parts.append(f"--- {filename} ---")
            parts.append(text.strip())
    else:
        parts.append("(No additional documents uploaded.)")

    # Template block
    parts.append("\n=== TEMPLATE & INSTRUCTIONS ===")
    if template_text.strip():
        parts.append(template_text.strip())
    else:
        parts.append("(No template provided — use a standard newsletter format.)")

    # Task instruction
    parts.append("\n=== YOUR TASK ===")
    parts.append(TASK_INSTRUCTION)

    return "\n\n".join(parts)
