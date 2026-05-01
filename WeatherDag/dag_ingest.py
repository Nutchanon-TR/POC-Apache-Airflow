"""
WeatherDag/dag_ingest.py
========================
DAG 1 — Weather Ingest (parameterized)

Pipeline:
    extract(forecast_days, cities) → transform → load → [trigger DAG 2]

Params (ตั้งได้ตอน trigger ใน Airflow UI):
    • forecast_days  : int  = 7         ← จำนวนวันที่ดึงจาก API (1–16)
    • cities         : list = [all 5]   ← เมืองที่ต้องการดึง
    • trigger_report : bool = True      ← ถ้า True จะ trigger weather_report ต่อ

Schedule: ทุกวัน 06:00 UTC
"""

from __future__ import annotations

import logging
from datetime import datetime

import requests
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import ShortCircuitOperator, get_current_context
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from config import (
    API_PARAMS, API_TIMEOUT, API_URL, CITIES,
    COLD_THRESHOLD_C, DAG_DEFAULT_ARGS, HOT_THRESHOLD_C,
    SUPABASE_KEY, SUPABASE_SCHEMA, SUPABASE_TABLE, SUPABASE_URL,
    WMO_CODES,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: EXTRACT
# ══════════════════════════════════════════════════════════════════════════════

@task
def extract_weather() -> list[dict]:
    """ดึงพยากรณ์อากาศตาม params (cities, forecast_days) → push XCom"""

    ctx           = get_current_context()
    forecast_days = ctx["params"]["forecast_days"]
    city_names    = ctx["params"]["cities"]

    # กรองเฉพาะเมืองที่ขอมา (ป้องกัน invalid city name)
    selected = {c: CITIES[c] for c in city_names if c in CITIES}
    if not selected:
        raise ValueError(f"ไม่มีเมืองที่ถูกต้องใน params: {city_names}")

    all_raw: list[dict] = []

    for city, coords in selected.items():
        url = (
            f"{API_URL}"
            f"?latitude={coords['lat']}&longitude={coords['lon']}"
            f"&daily={API_PARAMS}"
            f"&timezone=auto&forecast_days={forecast_days}"
        )
        logger.info("Fetching %s (%d days) ...", city, forecast_days)

        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()

        all_raw.append({
            "city":      city,
            "latitude":  coords["lat"],
            "longitude": coords["lon"],
            "raw_json":  response.json(),
        })
        logger.info("  ✓ %s", city)

    logger.info("Extract complete — %d cities", len(all_raw))
    return all_raw


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: TRANSFORM
# ══════════════════════════════════════════════════════════════════════════════

@task
def transform_weather(raw_data: list[dict]) -> list[dict]:
    """แปลง raw weather JSON เป็น flat records พร้อม metrics และ flags"""

    rows: list[dict] = []
    for record in raw_data:
        rows.extend(_flatten_city(record))

    logger.info("Transform complete — %d rows", len(rows))
    return rows


def _flatten_city(record: dict) -> list[dict]:
    """แปลง parallel arrays ของเมืองหนึ่ง → list of row dicts (ทีละวัน)"""

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
            "city":             record["city"],
            "latitude":         record["latitude"],
            "longitude":        record["longitude"],
            "date":             date,
            "temp_max_c":       t_max,
            "temp_min_c":       t_min,
            "temp_mean_c":      t_mean,
            "temp_range_c":     t_range,
            "precipitation_mm": prec,
            "windspeed_kmh":    wspd,
            "weather_summary":  WMO_CODES.get(code, f"Unknown ({code})"),
            "rain_flag":        prec is not None and prec > 0,
            "hot_flag":         t_max is not None and t_max >= HOT_THRESHOLD_C,
            "cold_flag":        t_min is not None and t_min <= COLD_THRESHOLD_C,
        })
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: LOAD
# ══════════════════════════════════════════════════════════════════════════════

@task
def load_weather(rows: list[dict]) -> int:
    """Insert weather rows เข้า Supabase airflow.weather"""

    headers = {
        "apikey":          SUPABASE_KEY,
        "Authorization":   f"Bearer {SUPABASE_KEY}",
        "Content-Type":    "application/json",
        "Content-Profile": SUPABASE_SCHEMA,
        "Prefer":          "return=minimal",
    }

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    response = requests.post(url, json=rows, headers=headers, timeout=API_TIMEOUT)
    response.raise_for_status()

    logger.info("Load complete — %d rows inserted", len(rows))
    return len(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: DAG
# ══════════════════════════════════════════════════════════════════════════════

@dag(
    dag_id="weather_ingest",
    default_args=DAG_DEFAULT_ARGS,
    description="Weather ingest: Open-Meteo API → Transform → Supabase → [trigger report]",
    schedule="0 6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["weather", "poc", "ingest"],
    doc_md=__doc__,
    params={
        "forecast_days":  Param(7,                 type="integer", minimum=1, maximum=16,
                                description="จำนวนวันพยากรณ์ที่ดึงจาก API"),
        "cities":         Param(list(CITIES.keys()), type="array",
                                description="รายชื่อเมืองที่ต้องการดึง"),
        "trigger_report": Param(True,              type="boolean",
                                description="True = trigger weather_report DAG ต่อ"),
    },
)
def weather_ingest() -> None:
    raw    = extract_weather()
    rows   = transform_weather(raw)
    loaded = load_weather(rows)

    # ShortCircuitOperator: ถ้า trigger_report=False จะ skip ทุก task ถัดไป
    gate = ShortCircuitOperator(
        task_id="should_trigger",
        python_callable=lambda **ctx: ctx["params"]["trigger_report"],
    )

    # TriggerDagRunOperator: trigger DAG 2 พร้อมส่ง run_date ไปด้วย
    # {{ ds }} = execution date ในรูปแบบ YYYY-MM-DD (Jinja template ของ Airflow)
    fire = TriggerDagRunOperator(
        task_id="trigger_report_dag",
        trigger_dag_id="weather_report",
        conf={"run_date": "{{ ds }}"},
        wait_for_completion=False,
    )

    loaded >> gate >> fire


weather_ingest()
