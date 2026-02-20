"""Uploaded file text extraction — supports .docx, .txt, .md."""
import io
from typing import Any
import mammoth


def extract_text(uploaded_file: Any) -> str:
    """
    Extract plain text from a Streamlit UploadedFile object.
    Supports: .docx, .txt, .md
    """
    name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)  # reset for any subsequent reads

    if name.endswith(".docx"):
        result = mammoth.extract_raw_text(io.BytesIO(raw_bytes))
        return result.value.strip()

    # .txt and .md: decode as UTF-8 with a fallback
    try:
        return raw_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1").strip()


def extract_all(uploaded_files: list) -> dict[str, str]:
    """
    Extract text from all uploaded files.
    Returns {filename: text} mapping.
    """
    results: dict[str, str] = {}
    for f in uploaded_files:
        try:
            results[f.name] = extract_text(f)
        except Exception as exc:
            results[f.name] = f"[Error extracting {f.name}: {exc}]"
    return results
