"""
WeatherDag/config.py
====================
Shared config สำหรับทั้ง dag_ingest และ dag_report
"""

from __future__ import annotations

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

# ─── DAG Defaults ────────────────────────────────────────────────────────────
DAG_DEFAULT_ARGS = {
    "owner":            "airflow",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
}

# ─── Open-Meteo API ──────────────────────────────────────────────────────────
API_URL       = "https://api.open-meteo.com/v1/forecast"
API_PARAMS    = "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode"
FORECAST_DAYS = 7
API_TIMEOUT   = 30

# ─── Cities ──────────────────────────────────────────────────────────────────
CITIES: dict[str, dict[str, float]] = {
    "Bangkok":  {"lat": 13.7563,  "lon": 100.5018},
    "Tokyo":    {"lat": 35.6762,  "lon": 139.6503},
    "London":   {"lat": 51.5074,  "lon":  -0.1278},
    "New York": {"lat": 40.7128,  "lon": -74.0060},
    "Sydney":   {"lat": -33.8688, "lon": 151.2093},
}

# ─── Thresholds ──────────────────────────────────────────────────────────────
HOT_THRESHOLD_C  = 35
COLD_THRESHOLD_C = 10

# ─── WMO Weather Codes ───────────────────────────────────────────────────────
WMO_CODES: dict[int, str] = {
    0:  "Clear sky",        1:  "Mainly clear",      2:  "Partly cloudy",    3:  "Overcast",
    45: "Fog",              48: "Rime fog",
    51: "Light drizzle",   53:  "Moderate drizzle",  55: "Dense drizzle",
    61: "Slight rain",     63:  "Moderate rain",     65: "Heavy rain",
    71: "Slight snow",     73:  "Moderate snow",     75: "Heavy snow",
    80: "Slight showers",  81:  "Moderate showers",  82: "Violent showers",
    95: "Thunderstorm",    96:  "Thunderstorm + slight hail", 99: "Thunderstorm + heavy hail",
}

# ─── Supabase ────────────────────────────────────────────────────────────────
SUPABASE_URL    = os.environ["SUPABASE_URL"]
SUPABASE_KEY    = os.environ["SUPABASE_KEY"]
SUPABASE_SCHEMA = "airflow"
SUPABASE_TABLE  = "weather"
