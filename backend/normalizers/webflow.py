import os


def normalize_webflow(raw: dict, params: dict = {}) -> str:
    items = raw.get("items", [])
    if not items:
        return "RECENT BLOG POSTS\nNo new posts in the last 7 days.\n"

    domain = os.getenv("WEBFLOW_SITE_DOMAIN", "your-site.webflow.io")
    lines = ["RECENT BLOG POSTS (last 7 days)"]
    for i, item in enumerate(items[:5], 1):
        fields = item.get("fieldData", item)
        title = fields.get("name", fields.get("title", "Untitled"))
        date = item.get("lastPublished", item.get("published-on", ""))[:10]
        summary = (fields.get("post-summary") or fields.get("description") or "")[:200]
        slug = fields.get("slug", "")
        url = f"https://{domain}/blog/{slug}"
        lines.append(
            f"{i}. {title} — Published {date}\n"
            f"   {summary}\n"
            f"   Read: {url}"
        )
    return "\n".join(lines) + "\n"
