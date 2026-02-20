from datetime import datetime


def normalize_luma(raw: dict, params: dict = {}) -> str:
    entries = raw.get("entries", []) or raw.get("events", []) or []
    if not entries:
        return "UPCOMING EVENTS\nNo events found in the next 21 days.\n"

    lines = ["UPCOMING EVENTS (next 21 days)"]
    for i, entry in enumerate(entries[:10], 1):
        event = entry.get("event", entry)
        title = event.get("name", "Untitled")
        start = event.get("start_at", "")
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            date_str = dt.strftime("%B %d, %Y at %I:%M %p %Z")
        except Exception:
            date_str = start
        geo = event.get("geo_address_info", {})
        location = geo.get("city") if geo else "Online"
        description = (event.get("description") or "")[:200]
        url = event.get("url", "")
        lines.append(
            f"{i}. {title} — {date_str} | {location or 'Online'}\n"
            f"   Description: {description}\n"
            f"   Register: {url}"
        )
    return "\n".join(lines) + "\n"
