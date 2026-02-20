import os
import requests
from datetime import datetime, timedelta, timezone


def fetch_luma_events(days_ahead: int = 21) -> dict:
    api_key = os.getenv("LUMA_API_KEY")
    headers = {"x-luma-api-key": api_key}

    # Fetch upcoming events from Luma
    url = "https://api.lu.ma/public/v1/calendar/list-events"
    params = {
        "after": datetime.now(timezone.utc).isoformat(),
        "before": (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat(),
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()
