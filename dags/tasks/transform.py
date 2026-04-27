"""
tasks/transform.py
==================
TRANSFORM — convert raw Open-Meteo JSON into flat, enriched records.

Input:  XCom["raw_weather"]   (from extract)
Output: XCom["transformed_weather"]
"""

from __future__ import annotations

import json
import logging

from config.settings import COLD_THRESHOLD_C, HOT_THRESHOLD_C, WMO_CODES

logger = logging.getLogger(__name__)


def transform_weather(**context) -> int:
    """Flatten and enrich raw weather data. No external dependencies."""
    raw_data: list[dict] = json.loads(
        context["ti"].xcom_pull(key="raw_weather", task_ids="extract")
    )

    rows: list[dict] = []
    for record in raw_data:
        rows.extend(_flatten_city(record))

    context["ti"].xcom_push(key="transformed_weather", value=json.dumps(rows, default=str))
    logger.info("Transform complete — %d rows", len(rows))
    return len(rows)


# ── Helpers ─────────────────────────────────────────────────────────────

def _flatten_city(record: dict) -> list[dict]:
    """Flatten one city's nested daily arrays into a list of row dicts."""
    daily    = record["raw_json"].get("daily", {})
    dates    = daily.get("time", [])
    temp_max = daily.get("temperature_2m_max", [])
    temp_min = daily.get("temperature_2m_min", [])
    precip   = daily.get("precipitation_sum", [])
    wind     = daily.get("windspeed_10m_max", [])
    codes    = daily.get("weathercode", [])

    rows: list[dict] = []
    for i, date in enumerate(dates):
        t_max = temp_max[i] if i < len(temp_max) else None
        t_min = temp_min[i] if i < len(temp_min) else None
        prec  = precip[i]   if i < len(precip)   else 0.0
        wspd  = wind[i]     if i < len(wind)      else None
        code  = int(codes[i]) if i < len(codes) and codes[i] is not None else None

        t_mean  = round((t_max + t_min) / 2, 2) if t_max is not None and t_min is not None else None
        t_range = round(t_max - t_min, 2)        if t_max is not None and t_min is not None else None

        rows.append({
            "city":              record["city"],
            "latitude":          record["latitude"],
            "longitude":         record["longitude"],
            "date":              date,
            "temp_max_c":        t_max,
            "temp_min_c":        t_min,
            "temp_mean_c":       t_mean,
            "temp_range_c":      t_range,
            "precipitation_mm":  prec,
            "windspeed_kmh":     wspd,
            "weather_summary":   WMO_CODES.get(code, f"Unknown ({code})"),
            "rain_flag":         prec is not None and prec > 0,
            "hot_flag":          t_max is not None and t_max >= HOT_THRESHOLD_C,
            "cold_flag":         t_min is not None and t_min <= COLD_THRESHOLD_C,
        })
    return rows
