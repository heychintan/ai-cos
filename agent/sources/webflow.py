"""Webflow CMS API — fetch and normalize job postings and blog posts."""
import httpx
from datetime import datetime, timezone, timedelta

WEBFLOW_BASE = "https://api.webflow.com/v2"


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "accept-version": "1.0.0",
        "Content-Type": "application/json",
    }


async def discover_jobs_collection(api_key: str) -> tuple[str, str, str]:
    """
    Auto-discover the first Webflow site's domain and jobs collection ID.
    Returns (site_id, site_domain, collection_id).
    """
    async with httpx.AsyncClient(timeout=15) as client:
        # 1. List sites
        sites_resp = await client.get(f"{WEBFLOW_BASE}/sites", headers=_headers(api_key))
        sites_resp.raise_for_status()
        sites = sites_resp.json().get("sites", [])
        if not sites:
            raise ValueError("No Webflow sites found for this API key.")

        site = sites[0]
        site_id = site["id"]
        # Prefer a custom domain; fall back to defaultDomain
        custom_domains = site.get("customDomains") or []
        if custom_domains:
            site_domain = custom_domains[0].get("url", "").lstrip("https://").lstrip("http://")
        else:
            site_domain = site.get("defaultDomain", "")

        # 2. List collections
        cols_resp = await client.get(
            f"{WEBFLOW_BASE}/sites/{site_id}/collections",
            headers=_headers(api_key),
        )
        cols_resp.raise_for_status()
        collections = cols_resp.json().get("collections", [])

    if not collections:
        raise ValueError("No CMS collections found in the Webflow site.")

    # Find a jobs/careers collection by name hint
    KEYWORDS = ("job", "career", "position", "opening", "role", "hiring")
    jobs_col = None
    for col in collections:
        name = col.get("displayName", "").lower()
        slug = col.get("slug", "").lower()
        if any(kw in name or kw in slug for kw in KEYWORDS):
            jobs_col = col
            break

    # Fall back to the first collection if no obvious match
    if not jobs_col:
        jobs_col = collections[0]

    return site_id, site_domain, jobs_col["id"]


async def fetch_webflow_jobs(
    api_key: str, collection_id: str = "", site_domain: str = "",
    days: int = 7, featured_first: bool = True,
) -> tuple[list[dict], str]:
    """
    Fetch published job postings from Webflow CMS.
    Returns (items, site_domain).

    Requires collection_id. site_domain is used for building Apply URLs.
    Falls back to auto-discovery only if collection_id is not provided.

    days: only include jobs whose created_time (fieldData.date) or Webflow
          createdOn is within the last N days.
    featured_first: if True, sort featured jobs (fieldData.featured == True) first.
    """
    if not collection_id:
        _, site_domain, collection_id = await discover_jobs_collection(api_key)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{WEBFLOW_BASE}/collections/{collection_id}/items",
            headers=_headers(api_key),
            params={"limit": 100},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    published: list[dict] = []
    for item in items:
        if item.get("isArchived", False) or item.get("isDraft", False):
            continue

        # Use fieldData.date (created_time field) first, fall back to item-level createdOn
        fd = item.get("fieldData") or {}
        raw_date = fd.get("date") or item.get("createdOn", "")
        if raw_date:
            try:
                item_dt = datetime.fromisoformat(str(raw_date).rstrip("Z")).replace(tzinfo=timezone.utc)
                if item_dt < cutoff:
                    continue
            except (ValueError, AttributeError):
                pass  # unparseable date — include the item

        published.append(item)

    # Featured jobs first when requested
    if featured_first:
        published.sort(key=lambda x: not bool((x.get("fieldData") or {}).get("featured")))

    return published[:10], site_domain


async def fetch_webflow_blogs(
    api_key: str, collection_id: str, site_domain: str = "",
    days: int = 7, featured_first: bool = True,
) -> tuple[list[dict], str]:
    """
    Fetch published blog posts from a Webflow CMS collection.
    Returns (items, site_domain). No auto-discovery — collection_id is required.

    days: only include posts whose publish-date is within the last N days.
    featured_first: if True, sort featured posts (fieldData.featured == True) first.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{WEBFLOW_BASE}/collections/{collection_id}/items",
            headers=_headers(api_key),
            params={"limit": 100},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    published: list[dict] = []
    for item in items:
        if item.get("isArchived", False) or item.get("isDraft", False):
            continue

        # Use publish-date field first, fall back to item-level createdOn
        fd = item.get("fieldData") or {}
        raw_date = fd.get("publish-date") or item.get("createdOn", "")
        if raw_date:
            try:
                item_dt = datetime.fromisoformat(str(raw_date).rstrip("Z")).replace(tzinfo=timezone.utc)
                if item_dt < cutoff:
                    continue
            except (ValueError, AttributeError):
                pass  # unparseable date — include the item

        published.append(item)

    # Featured posts first when requested
    if featured_first:
        published.sort(key=lambda x: not bool((x.get("fieldData") or {}).get("featured")))

    return published[:10], site_domain


def normalize_webflow_blogs(
    posts: list[dict], site_domain: str = "",
    days: int = 7, featured_first: bool = True,
) -> str:
    featured_note = ", featured first" if featured_first else ""
    header = f"RECENT BLOG POSTS (last {days} days{featured_note})"
    if not posts:
        return f"{header}\nNo blog posts found.\n"

    lines = [header]
    for i, post in enumerate(posts, 1):
        fd = post.get("fieldData") or {}

        title = fd.get("name") or post.get("name", "Untitled Post")
        slug = fd.get("slug") or post.get("slug", "")
        is_featured = bool(fd.get("featured"))

        # Publish date (schema: publish-date, DateTime, required)
        publish_date = str(fd.get("publish-date") or "")[:10]

        # Reading time (schema: reading-time, Number, required)
        reading_time = fd.get("reading-time")

        # Summary/excerpt (schema: meta-description, PlainText)
        summary = str(fd.get("meta-description") or "")

        # Author is a Reference (returns an ID, not a name — include if a string)
        author = fd.get("author") if isinstance(fd.get("author"), str) else ""

        featured_tag = " ★" if is_featured else ""
        title_line = f"{i}. {title}{featured_tag}"
        meta_parts = [p for p in [publish_date, f"{reading_time} min read" if reading_time else "", author] if p]
        if meta_parts:
            title_line += " · " + " · ".join(meta_parts)
        lines.append(title_line)

        if summary:
            preview = summary[:200].strip()
            if len(summary) > 200:
                preview += "…"
            lines.append(f"   {preview}")

        if site_domain and slug:
            domain = site_domain.rstrip("/")
            lines.append(f"   URL: https://{domain}/blog/{slug}")

        lines.append("")

    return "\n".join(lines)


def normalize_webflow_jobs(
    jobs: list[dict], site_domain: str = "",
    days: int = 7, featured_first: bool = True,
) -> str:
    featured_note = ", featured first" if featured_first else ""
    header = f"JOB POSTINGS (last {days} days{featured_note})"
    if not jobs:
        return f"{header}\nNo job postings found.\n"

    lines = [header]
    for i, job in enumerate(jobs, 1):
        fd = job.get("fieldData") or {}

        # Job title
        title = (
            fd.get("name")
            or fd.get("title")
            or fd.get("job-title")
            or job.get("name", "Untitled Position")
        )

        slug = fd.get("slug") or job.get("slug", "")
        is_featured = bool(fd.get("featured"))

        # Meta fields — mapped from Jobs schema
        location = fd.get("location") or ""          # location_name
        country  = fd.get("location-country") or ""  # country
        job_type = fd.get("type") or ""               # employment_status (Option)
        workplace = fd.get("workplace-type") or ""    # workplace_type (Option)
        seniority = fd.get("seniority") or ""         # experience_level (Option)
        salary    = fd.get("salary") or ""            # salary
        remote    = fd.get("remote")                  # remote (Switch)

        # Build location string
        location_parts = [p for p in [location, country] if p]
        location_str = ", ".join(location_parts)
        if remote and not workplace:
            location_str = f"{location_str} (Remote)".strip() if location_str else "Remote"

        meta_parts = [p for p in [job_type, workplace or ("Remote" if remote else ""), seniority, location_str, salary] if p]
        meta = " | ".join(meta_parts)

        # Date posted
        raw_date = fd.get("date") or job.get("createdOn", "")
        date_str = str(raw_date)[:10] if raw_date else ""

        # Description
        description = str(fd.get("job-description") or fd.get("description") or "")

        desc_preview = description[:200].strip()
        if len(description) > 200:
            desc_preview += "…"

        featured_tag = " ★" if is_featured else ""
        title_line = f"{i}. {title}{featured_tag}"
        if date_str:
            title_line += f" · Posted {date_str}"
        if meta:
            title_line += f" — {meta}"
        lines.append(title_line)

        if desc_preview:
            lines.append(f"   {desc_preview}")

        # Apply method
        if fd.get("use-email-instead-of-link") and fd.get("apply-mail"):
            lines.append(f"   Apply: {fd['apply-mail']}")
        elif fd.get("application-link"):
            lines.append(f"   Apply: {fd['application-link']}")
        elif site_domain and slug:
            domain = site_domain.rstrip("/")
            lines.append(f"   Apply: https://{domain}/jobs/{slug}")

        lines.append("")

    return "\n".join(lines)
