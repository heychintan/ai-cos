"""Background task execution — runs the full pipeline in a daemon thread."""
from __future__ import annotations

import asyncio
import io
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_results: Dict[str, Dict] = {}
_lock = threading.Lock()


# ── Result accessors ──────────────────────────────────────────────────────────

def poll_result(task_id: str) -> Optional[Dict]:
    with _lock:
        r = _results.get(task_id)
        return dict(r) if r else None


def clear_result(task_id: str) -> None:
    with _lock:
        _results.pop(task_id, None)


# ── Pipeline ──────────────────────────────────────────────────────────────────

def _extract_bytes(name: str, data: bytes) -> str:
    import mammoth
    if name.lower().endswith(".docx"):
        return mammoth.extract_raw_text(io.BytesIO(data)).value.strip()
    return data.decode("utf-8", errors="replace").strip()


def _run_pipeline(task: Dict[str, Any], api_config: Dict[str, str]) -> Dict[str, Any]:
    """Full fetch → normalize → generate → docx pipeline. Runs synchronously."""
    from agent.sources.luma import fetch_luma_events, normalize_luma
    from agent.sources.spotify import fetch_spotify_episodes, normalize_spotify
    from agent.sources.webflow import (
        fetch_webflow_jobs, normalize_webflow_jobs,
        fetch_webflow_blogs, normalize_webflow_blogs,
    )
    from agent.context import assemble_context
    from agent.claude import generate_text
    from agent.output import generate_docx

    src = task["sources"]

    # 1. Fetch all sources in parallel
    async def _fetch():
        coros: Dict[str, Any] = {}
        if src["luma"]["enabled"] and api_config.get("luma_key"):
            coros["luma"] = fetch_luma_events(api_config["luma_key"], src["luma"]["days"])
        if src["spotify"]["enabled"] and api_config.get("spotify_id") and api_config.get("spotify_secret"):
            coros["spotify"] = fetch_spotify_episodes(
                api_config["spotify_id"], api_config["spotify_secret"], src["spotify"]["days"]
            )
        if src["webflow"]["enabled"] and api_config.get("webflow_key"):
            coros["webflow"] = fetch_webflow_jobs(
                api_config["webflow_key"],
                api_config.get("webflow_jobs_collection", ""),
                api_config.get("webflow_domain", ""),
            )
        if src.get("webflow_blogs", {}).get("enabled") and api_config.get("webflow_key") and api_config.get("webflow_blogs_collection"):
            coros["webflow_blogs"] = fetch_webflow_blogs(
                api_config["webflow_key"],
                api_config["webflow_blogs_collection"],
                api_config.get("webflow_domain", ""),
            )
        if not coros:
            return {}
        gathered = await asyncio.gather(*coros.values(), return_exceptions=True)
        return dict(zip(coros.keys(), gathered))

    loop = asyncio.new_event_loop()
    try:
        raw = loop.run_until_complete(_fetch())
    finally:
        loop.close()

    # 2. Normalize
    luma_text = spotify_text = webflow_text = blogs_text = ""
    sources_used: list = []

    if "luma" in raw:
        r = raw["luma"]
        if isinstance(r, Exception):
            sources_used.append(f"Luma (error: {r})")
        else:
            luma_text = normalize_luma(r, src["luma"]["days"])
            sources_used.append(f"Luma ({len(r)} events)")

    if "spotify" in raw:
        r = raw["spotify"]
        if isinstance(r, Exception):
            sources_used.append(f"Spotify (error: {r})")
        else:
            spotify_text = normalize_spotify(r, src["spotify"]["days"])
            sources_used.append(f"Spotify ({len(r)} episodes)")

    if "webflow" in raw:
        r = raw["webflow"]
        if isinstance(r, Exception):
            sources_used.append(f"Webflow Jobs (error: {r})")
        else:
            jobs, domain = r
            webflow_text = normalize_webflow_jobs(jobs, domain)
            sources_used.append(f"Webflow Jobs ({len(jobs)} jobs)")

    if "webflow_blogs" in raw:
        r = raw["webflow_blogs"]
        if isinstance(r, Exception):
            sources_used.append(f"Webflow Blogs (error: {r})")
        else:
            posts, domain = r
            blogs_text = normalize_webflow_blogs(posts, domain)
            sources_used.append(f"Webflow Blogs ({len(posts)} posts)")

    # 3. Extract uploaded files
    template_text = ""
    if task.get("template"):
        template_text = _extract_bytes(task["template"]["name"], task["template"]["bytes"])

    uploaded_docs: Dict[str, str] = {}
    for doc in task.get("context_docs", []):
        uploaded_docs[doc["name"]] = _extract_bytes(doc["name"], doc["bytes"])

    # Append custom instructions
    if task.get("instructions"):
        template_text = (
            (template_text + "\n\n" + task["instructions"]).strip()
            if template_text else task["instructions"]
        )

    # 4. Assemble context
    context = assemble_context(
        luma_text=luma_text,
        spotify_text=spotify_text,
        webflow_text=webflow_text,
        blogs_text=blogs_text,
        uploaded_docs=uploaded_docs or None,
        template_text=template_text,
    )

    # 5. Generate (non-streaming — runs in background thread)
    full_text = generate_text(
        api_key=api_config["anthropic_key"],
        context=context,
        model=task["model"],
    )

    # 6. Build .docx
    docx_bytes = generate_docx(full_text, task["model"])

    return {
        "status":      "done",
        "output":      full_text,
        "docx_bytes":  docx_bytes,
        "sources_used": sources_used,
        "timestamp":   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def _worker(task_id: str, task: Dict[str, Any], api_config: Dict[str, str]) -> None:
    try:
        result = _run_pipeline(task, api_config)
        with _lock:
            _results[task_id] = result
    except Exception as exc:
        with _lock:
            _results[task_id] = {
                "status":    "error",
                "error":     str(exc),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }


def submit_task(task: Dict[str, Any], api_config: Dict[str, str]) -> None:
    """Submit a task for background execution. Non-blocking."""
    with _lock:
        _results[task["id"]] = {"status": "running"}
    t = threading.Thread(target=_worker, args=(task["id"], task, api_config), daemon=True)
    t.start()
