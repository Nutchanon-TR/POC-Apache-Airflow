"""
WeatherDag/dag_report.py
========================
DAG 2 — Weather Report (standalone / triggerable)

อ่านข้อมูลจาก Supabase แล้ว report ออก Airflow log
Trigger ได้ 2 แบบ:
  1. อัตโนมัติ — ถูก trigger จาก weather_ingest (ถ้า trigger_report=True)
  2. Manual   — trigger เองใน Airflow UI พร้อมระบุ run_date

Params:
    • run_date : str = "" → ถ้าว่างจะใช้วันที่วันนี้ (YYYY-MM-DD)
"""

from __future__ import annotations

import logging
from datetime import date, datetime

import requests
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context

from config import (
    API_TIMEOUT, DAG_DEFAULT_ARGS,
    SUPABASE_KEY, SUPABASE_SCHEMA, SUPABASE_TABLE, SUPABASE_URL,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: FETCH
# ══════════════════════════════════════════════════════════════════════════════

@task
def fetch_from_supabase() -> list[dict]:
    """อ่านข้อมูลจาก Supabase airflow.weather ตาม run_date"""

    ctx      = get_current_context()
    run_date = ctx["params"].get("run_date") or str(date.today())

    headers = {
        "apikey":         SUPABASE_KEY,
        "Authorization":  f"Bearer {SUPABASE_KEY}",
        "Accept-Profile": SUPABASE_SCHEMA,
    }

    # PostgREST filter syntax: ?column=eq.value
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?dag_run_date=eq.{run_date}"
    response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()

    rows = response.json()
    logger.info("Fetched %d rows for run_date=%s", len(rows), run_date)
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: REPORT
# ══════════════════════════════════════════════════════════════════════════════

@task
def report_weather(rows: list[dict]) -> int:
    """Print ข้อมูลพยากรณ์อากาศทุกเมืองแบบตาราง ออก Airflow log"""

    if not rows:
        logger.warning("ไม่มีข้อมูลใน Supabase สำหรับวันที่นี้")
        return 0

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
                "HOT"  if f.get("hot_flag")  else "",
                "COLD" if f.get("cold_flag") else "",
                "RAIN" if f.get("rain_flag") else "",
            ])) or "-"

            logger.info(
                "  %-12s %-22s %6s %6s %8s %s",
                f.get("date"),
                f.get("weather_summary"),
                f.get("temp_max_c") if f.get("temp_max_c") is not None else "N/A",
                f.get("temp_min_c") if f.get("temp_min_c") is not None else "N/A",
                f.get("precipitation_mm"),
                flags,
            )

    logger.info("\nTotal rows: %d", len(rows))
    logger.info("=" * 60)
    return len(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: DAG
# ══════════════════════════════════════════════════════════════════════════════

@dag(
    dag_id="weather_report",
    default_args=DAG_DEFAULT_ARGS,
    description="Weather report: อ่านจาก Supabase → Log",
    schedule="30 6 * * *",      # ทุกวัน 06:30 UTC (30 นาทีหลัง DAG1 run)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["weather", "poc", "report"],
    doc_md=__doc__,
    params={
        "run_date": Param("", type="string",
                          description="วันที่ต้องการ report (YYYY-MM-DD) — ว่าง = วันนี้"),
    },
)
def weather_report() -> None:
    rows = fetch_from_supabase()
    report_weather(rows)


weather_report()
