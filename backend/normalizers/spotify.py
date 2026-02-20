def normalize_spotify(raw: dict, params: dict = {}) -> str:
    items = raw.get("items", [])
    if not items:
        return "RECENT PODCAST EPISODES\nNo new episodes in the last 7 days.\n"

    lines = ["RECENT PODCAST EPISODES (last 7 days)"]
    for i, ep in enumerate(items[:5], 1):
        title = ep.get("name", "Untitled")
        date = ep.get("release_date", "")
        duration_ms = ep.get("duration_ms", 0)
        duration_min = round(duration_ms / 60000)
        description = (ep.get("description") or "")[:200]
        url = ep.get("external_urls", {}).get("spotify", "")
        lines.append(
            f"{i}. {title} — Released {date} | {duration_min} mins\n"
            f"   {description}\n"
            f"   Listen: {url}"
        )
    return "\n".join(lines) + "\n"
