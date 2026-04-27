"""
tasks/extract.py
================
EXTRACT — fetch 7-day weather forecast from Open-Meteo API.

Output: pushes raw JSON list to XCom["raw_weather"]
"""

from __future__ import annotations

import json
import logging

import requests

from config.settings import API_PARAMS, API_TIMEOUT, API_URL, CITIES, FORECAST_DAYS

logger = logging.getLogger(__name__)


def extract_weather(**context) -> int:
    """Fetch forecast for every city and push raw responses to XCom."""
    all_raw: list[dict] = []

    for city, coords in CITIES.items():
        url = (
            f"{API_URL}"
            f"?latitude={coords['lat']}&longitude={coords['lon']}"
            f"&daily={API_PARAMS}"
            f"&timezone=auto&forecast_days={FORECAST_DAYS}"
        )
        logger.info("Fetching %s ...", city)

        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()

        all_raw.append({
            "city":      city,
            "latitude":  coords["lat"],
            "longitude": coords["lon"],
            "raw_json":  response.json(),
        })
        logger.info("  ✓ %s — %d days", city, len(response.json().get("daily", {}).get("time", [])))

    context["ti"].xcom_push(key="raw_weather", value=json.dumps(all_raw))
    logger.info("Extract complete — %d cities", len(all_raw))
    return len(all_raw)
