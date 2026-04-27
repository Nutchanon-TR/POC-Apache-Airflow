"""
tasks/report.py
===============
REPORT — log transformed weather data to Airflow task logs.

Input:  XCom["transformed_weather"]  (from transform)
Output: formatted log output visible in Airflow UI
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def report_weather(**context) -> int:
    """Print a summary of transformed weather data to the task log."""
    rows: list[dict] = json.loads(
        context["ti"].xcom_pull(key="transformed_weather", task_ids="transform")
    )

    # Group by city for readable output
    by_city: dict[str, list[dict]] = {}
    for row in rows:
        by_city.setdefault(row["city"], []).append(row)

    logger.info("=" * 60)
    logger.info("WEATHER FORECAST REPORT")
    logger.info("=" * 60)

    for city, forecasts in by_city.items():
        logger.info("\n[%s]", city)
        logger.info("  %-12s %-22s %6s %6s %8s %s", "Date", "Summary", "Max°C", "Min°C", "Rain mm", "Flags")
        logger.info("  " + "-" * 70)
        for f in forecasts:
            flags = " ".join(filter(None, [
                "HOT"  if f["hot_flag"]  else "",
                "COLD" if f["cold_flag"] else "",
                "RAIN" if f["rain_flag"] else "",
            ])) or "-"
            logger.info(
                "  %-12s %-22s %6s %6s %8s %s",
                f["date"],
                f["weather_summary"],
                f["temp_max_c"] if f["temp_max_c"] is not None else "N/A",
                f["temp_min_c"] if f["temp_min_c"] is not None else "N/A",
                f["precipitation_mm"],
                flags,
            )

    logger.info("\nTotal rows: %d", len(rows))
    logger.info("=" * 60)
    return len(rows)
