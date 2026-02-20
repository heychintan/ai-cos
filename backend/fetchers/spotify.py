import os
import requests
from datetime import datetime, timedelta, timezone


def _get_access_token() -> str:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_spotify_episodes(show_id: str, days_back: int = 7) -> dict:
    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/shows/{show_id}/episodes"
    params = {"limit": 10, "market": "US"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    recent = [
        ep for ep in data.get("items", [])
        if ep.get("release_date") and
        datetime.fromisoformat(ep["release_date"]).replace(tzinfo=timezone.utc) >= cutoff
    ]
    return {"items": recent}
