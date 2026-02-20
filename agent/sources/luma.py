"""Luma Events API — fetch and normalize upcoming events."""
import httpx
from datetime import datetime, timezone, timedelta

CALENDAR_ID = "cal-9Z75SHNwmRJPyWb"
BASE_URL = "https://public-api.luma.com/v1/calendar/list-events"


async def fetch_luma_events(api_key: str, days: int = 21) -> list[dict]:
    """Fetch upcoming events from the CoSN Luma calendar."""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    params = {
        "after": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "before": cutoff.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "sort_column": "start_at",
        "sort_direction": "asc",
        "pagination_limit": 10,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            BASE_URL,
            headers={"accept": "application/json", "x-luma-api-key": api_key},
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    events = [entry.get("event", {}) for entry in data.get("entries", [])]
    return events


def normalize_luma(events: list[dict], days: int = 21) -> str:
    header = f"UPCOMING EVENTS (next {days} days)"
    if not events:
        return f"{header}\nNo upcoming events found.\n"

    lines = [header]
    for i, event in enumerate(events, 1):
        title = event.get("name", "Untitled Event")
        start_at = event.get("start_at", "")
        url = event.get("url", "")
        description = event.get("description", "") or ""

        geo = event.get("geo_address_info") or {}
        location = (
            geo.get("city_state")
            or geo.get("city")
            or geo.get("description")
            or "Online"
        )

        if start_at:
            try:
                dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
                date_str = dt.strftime("%b %d, %Y at %I:%M %p UTC")
            except ValueError:
                date_str = start_at
        else:
            date_str = "TBD"

        desc_preview = description[:200].strip()
        if len(description) > 200:
            desc_preview += "…"

        lines.append(f"{i}. {title} — {date_str} | {location}")
        if desc_preview:
            lines.append(f"   {desc_preview}")
        if url:
            lines.append(f"   Register: {url}")
        lines.append("")

    return "\n".join(lines)
