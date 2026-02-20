import os
import requests
from datetime import datetime, timedelta, timezone


def fetch_webflow_posts(days_back: int = 7) -> dict:
    api_key = os.getenv("WEBFLOW_API_KEY")
    collection_id = os.getenv("WEBFLOW_COLLECTION_ID")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "accept-version": "1.0.0",
    }
    url = f"https://api.webflow.com/collections/{collection_id}/items"
    params = {"limit": 20}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    recent = [
        item for item in data.get("items", [])
        if item.get("published-on") and
        datetime.fromisoformat(item["published-on"].replace("Z", "+00:00")) >= cutoff
    ]
    return {"items": recent}
