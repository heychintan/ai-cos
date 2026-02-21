"""Task model — factory, helpers, constants."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

MIN_INTERVAL = 60  # seconds

INTERVAL_PRESETS: Dict[str, int] = {
    "1 min":    60,
    "5 min":    300,
    "15 min":   900,
    "30 min":   1800,
    "1 hour":   3600,
    "6 hours":  21600,
    "12 hours": 43200,
    "24 hours": 86400,
}


def fmt_interval(seconds: int) -> str:
    if seconds < 3600:
        m = seconds // 60
        return f"{m} min"
    elif seconds < 86400:
        h = seconds // 3600
        return f"{h} hr"
    else:
        d = seconds // 86400
        return f"{d} day{'s' if d > 1 else ''}"


def fmt_dt(dt: Optional[datetime]) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%b %d %H:%M")


def new_task(
    name: str,
    instructions: str,
    interval: int,
    model: str,
    luma_enabled: bool,
    luma_days: int,
    spotify_enabled: bool,
    spotify_days: int,
    webflow_enabled: bool,
    template: Optional[Dict[str, Any]],
    context_docs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "id":           str(uuid.uuid4()),
        "name":         name,
        "instructions": instructions,
        "interval":     max(interval, MIN_INTERVAL),
        "model":        model,
        "sources": {
            "luma":    {"enabled": luma_enabled,    "days": luma_days},
            "spotify": {"enabled": spotify_enabled, "days": spotify_days},
            "webflow": {"enabled": webflow_enabled},
        },
        "template":     template,      # {"name": str, "bytes": bytes} | None
        "context_docs": context_docs,  # [{"name": str, "bytes": bytes}]
        "enabled":    True,
        "status":     "idle",          # idle | running | done | error
        "last_run":   None,
        "next_run":   None,
        "last_error": "",
        "outputs":    [],              # newest first, max 5
    }


def schedule_next(task: Dict[str, Any], from_dt: Optional[datetime] = None) -> None:
    base = from_dt or datetime.now(timezone.utc)
    task["next_run"] = base + timedelta(seconds=task["interval"])
