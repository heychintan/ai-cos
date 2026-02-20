"""Luma Events API — fetch and normalize upcoming events."""
import httpx
from datetime import datetime, timezone, timedelta

CALENDAR_ID = "cal-9Z75SHNwmRJPyWb"
BASE_URL = "https://api.lu.ma/v1/calendar/list-events"


async def fetch_luma_events(api_key: str, days: int = 21) -> list[dict]:
    """Fetch upcoming events from the CoSN Luma calendar."""
    headers = {"x-luma-api-key": api_key}
    params = {"calendar_api_id": CALENDAR_ID}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(BASE_URL, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    events: list[dict] = []
    for entry in data.get("entries", []):
        event = entry.get("event", {})
        start_at = event.get("start_at", "")
        if start_at:
            try:
                start_dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
                if now <= start_dt <= cutoff:
                    events.append(event)
            except ValueError:
                pass

    events.sort(key=lambda e: e.get("start_at", ""))
    return events[:10]


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
