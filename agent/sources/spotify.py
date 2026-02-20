"""Spotify Podcast API — fetch and normalize recent episodes."""
from __future__ import annotations

import base64
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional

SHOW_ID = "0mroNmOfEqWdkPEYYtN3PF"
TOKEN_URL = "https://accounts.spotify.com/api/token"
EPISODES_URL = f"https://api.spotify.com/v1/shows/{SHOW_ID}/episodes"


async def _get_token(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


def _parse_release_date(release_date: str) -> Optional[datetime]:
    """Handle Spotify's variable date precision: YYYY, YYYY-MM, YYYY-MM-DD."""
    formats = ["%Y-%m-%d", "%Y-%m", "%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(release_date, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


async def fetch_spotify_episodes(
    client_id: str, client_secret: str, days: int = 7
) -> list[dict]:
    """Fetch recent CoSN podcast episodes from Spotify."""
    token = await _get_token(client_id, client_secret)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            EPISODES_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 50, "market": "US"},
        )
        resp.raise_for_status()
        data = resp.json()

    episodes: list[dict] = []
    for ep in data.get("items", []):
        if ep is None:
            continue
        release_date = ep.get("release_date", "")
        if release_date:
            release_dt = _parse_release_date(release_date)
            if release_dt and release_dt >= cutoff:
                episodes.append(ep)

    episodes.sort(key=lambda e: e.get("release_date", ""), reverse=True)
    return episodes[:10]


def normalize_spotify(episodes: list[dict], days: int = 7) -> str:
    header = f"RECENT PODCAST EPISODES (last {days} days)"
    if not episodes:
        return f"{header}\nNo recent episodes found.\n"

    lines = [header]
    for i, ep in enumerate(episodes, 1):
        name = ep.get("name", "Untitled Episode")
        description = ep.get("description", "") or ""
        release_date = ep.get("release_date", "Unknown")
        duration_ms = ep.get("duration_ms", 0) or 0
        duration_min = round(duration_ms / 60000)
        url = (ep.get("external_urls") or {}).get("spotify", "")

        desc_preview = description[:200].strip()
        if len(description) > 200:
            desc_preview += "…"

        lines.append(f"{i}. {name} — Released {release_date} | {duration_min} mins")
        if desc_preview:
            lines.append(f"   {desc_preview}")
        if url:
            lines.append(f"   Listen: {url}")
        lines.append("")

    return "\n".join(lines)
