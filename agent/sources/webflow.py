"""Webflow CMS API — fetch and normalize job postings and blog posts."""
import httpx

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
    api_key: str, collection_id: str = "", site_domain: str = ""
) -> tuple[list[dict], str]:
    """
    Fetch published job postings from Webflow CMS.
    Returns (items, site_domain).

    Requires collection_id. site_domain is used for building Apply URLs.
    Falls back to auto-discovery only if collection_id is not provided.
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

    # Only published, non-archived items
    published = [
        item for item in items
        if not item.get("isArchived", False) and not item.get("isDraft", False)
    ]
    return published[:10], site_domain


async def fetch_webflow_blogs(api_key: str, collection_id: str, site_domain: str = "") -> tuple[list[dict], str]:
    """
    Fetch published blog posts from a Webflow CMS collection.
    Returns (items, site_domain). No auto-discovery — collection_id is required.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{WEBFLOW_BASE}/collections/{collection_id}/items",
            headers=_headers(api_key),
            params={"limit": 100},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])

    published = [
        item for item in items
        if not item.get("isArchived", False) and not item.get("isDraft", False)
    ]
    return published[:10], site_domain


def normalize_webflow_blogs(posts: list[dict], site_domain: str = "") -> str:
    header = "RECENT BLOG POSTS"
    if not posts:
        return f"{header}\nNo blog posts found.\n"

    lines = [header]
    for i, post in enumerate(posts, 1):
        fd = post.get("fieldData") or {}

        title = (
            fd.get("name")
            or fd.get("title")
            or fd.get("post-title")
            or post.get("name", "Untitled Post")
        )

        slug = fd.get("slug") or post.get("slug", "")

        publish_date = (
            fd.get("publish-date")
            or fd.get("date")
            or fd.get("published-on")
            or ""
        )
        if publish_date:
            # Trim to date portion if ISO datetime
            publish_date = str(publish_date)[:10]

        author = fd.get("author") or fd.get("writer") or ""

        excerpt = str(
            fd.get("excerpt")
            or fd.get("summary")
            or fd.get("description")
            or fd.get("short-description")
            or ""
        )

        meta_parts = [p for p in [publish_date, author] if p]
        meta = " · ".join(meta_parts)

        excerpt_preview = excerpt[:200].strip()
        if len(excerpt) > 200:
            excerpt_preview += "…"

        lines.append(f"{i}. {title}" + (f" — {meta}" if meta else ""))
        if excerpt_preview:
            lines.append(f"   {excerpt_preview}")
        if site_domain and slug:
            domain = site_domain.rstrip("/")
            lines.append(f"   URL: https://{domain}/blog/{slug}")
        lines.append("")

    return "\n".join(lines)


def normalize_webflow_jobs(jobs: list[dict], site_domain: str = "") -> str:
    header = "FEATURED JOB POSTINGS"
    if not jobs:
        return f"{header}\nNo job postings found.\n"

    lines = [header]
    for i, job in enumerate(jobs, 1):
        fd = job.get("fieldData") or {}

        # Job title — try multiple common field names
        title = (
            fd.get("name")
            or fd.get("title")
            or fd.get("job-title")
            or job.get("name", "Untitled Position")
        )

        slug = fd.get("slug") or job.get("slug", "")

        # Meta fields
        department = fd.get("department") or fd.get("team") or fd.get("category") or ""
        location = (
            fd.get("location")
            or fd.get("city")
            or fd.get("office")
            or fd.get("work-location")
            or ""
        )
        job_type = (
            fd.get("type")
            or fd.get("employment-type")
            or fd.get("job-type")
            or fd.get("work-type")
            or ""
        )

        # Description
        description = str(
            fd.get("description")
            or fd.get("summary")
            or fd.get("excerpt")
            or fd.get("short-description")
            or ""
        )

        meta_parts = [p for p in [department, location, job_type] if p]
        meta = " | ".join(meta_parts)

        desc_preview = description[:200].strip()
        if len(description) > 200:
            desc_preview += "…"

        lines.append(f"{i}. {title}" + (f" — {meta}" if meta else ""))
        if desc_preview:
            lines.append(f"   {desc_preview}")
        if site_domain and slug:
            domain = site_domain.rstrip("/")
            lines.append(f"   Apply: https://{domain}/jobs/{slug}")
        lines.append("")

    return "\n".join(lines)
