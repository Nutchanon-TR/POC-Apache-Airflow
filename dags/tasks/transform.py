"""
tasks/transform.py
==================
TRANSFORM — แปลง raw JSON เป็น records ที่ใช้งานได้ + คำนวณ metrics

Input:  XCom["raw_weather"]         (จาก extract task)
Output: XCom["transformed_weather"] (ส่งให้ report task)

ไม่มี external dependencies — ใช้แค่ Python standard library
"""

from __future__ import annotations

import json
import logging

# import เฉพาะ constant ที่ต้องใช้ จาก settings.py
from config.settings import COLD_THRESHOLD_C, HOT_THRESHOLD_C, WMO_CODES

logger = logging.getLogger(__name__)


# ─── Main Function ──────────────────────────────────────────────────────────

def transform_weather(**context) -> int:
    """แปลง raw weather JSON เป็น flat records พร้อม metrics และ flags"""

    # xcom_pull() = ดึงข้อมูลที่ task อื่น push ไว้
    # task_ids="extract" = บอกว่าดึงจาก task ชื่อ "extract"
    # key="raw_weather"  = ดึง key นี้
    raw_data: list[dict] = json.loads(
        context["ti"].xcom_pull(key="raw_weather", task_ids="extract")
    )

    # list comprehension + extend
    # rows = [] แล้วค่อย loop เพิ่มทีละ city
    rows: list[dict] = []
    for record in raw_data:
        # extend() เพิ่มทุก element จาก list เข้า list หลัก (ไม่ใช่ append list เป็น element เดียว)
        # เทียบ JS: rows.push(..._flattenCity(record))
        rows.extend(_flatten_city(record))

    # json.dumps() แปลง Python list → JSON string เพื่อเก็บใน XCom
    # default=str บอกว่า ถ้าเจอ type ที่ serialize ไม่ได้ ให้แปลงเป็น string แทน
    context["ti"].xcom_push(key="transformed_weather", value=json.dumps(rows, default=str))

    logger.info("Transform complete — %d rows", len(rows))
    return len(rows)


# ─── Helper Function ────────────────────────────────────────────────────────

# ชื่อฟังก์ชันขึ้นต้นด้วย _ (underscore) = convention บอกว่าเป็น "private"
# เหมือน private method ใน Java แต่ Python ไม่บังคับ — เป็นแค่ข้อตกลง
def _flatten_city(record: dict) -> list[dict]:
    """แปลง nested array ของเมืองหนึ่ง → list of row dicts (ทีละวัน)

    Open-Meteo API ส่งข้อมูลมาแบบ "parallel arrays":
    { "time": ["2025-01-01", "2025-01-02", ...],
      "temperature_2m_max": [36.5, 34.1, ...],
      ... }

    เราต้องแปลงเป็น row-based (ทีละวัน):
    [{ "date": "2025-01-01", "temp_max_c": 36.5, ... },
     { "date": "2025-01-02", "temp_max_c": 34.1, ... }, ...]
    """

    # .get(key, default) = ดึง value จาก dict ถ้าไม่มี key นั้นจะคืน default
    # เทียบ JS: record.raw_json?.daily ?? {}
    daily    = record["raw_json"].get("daily", {})
    dates    = daily.get("time", [])
    temp_max = daily.get("temperature_2m_max", [])
    temp_min = daily.get("temperature_2m_min", [])
    precip   = daily.get("precipitation_sum", [])
    wind     = daily.get("windspeed_10m_max", [])
    codes    = daily.get("weathercode", [])

    rows: list[dict] = []

    # enumerate() คืน (index, value) ใน for loop
    # เทียบ JS: dates.forEach((date, i) => ...)
    for i, date in enumerate(dates):

        # Ternary operator ใน Python: value_if_true if condition else value_if_false
        # ลำดับกลับกันจาก JS ซึ่งเป็น: condition ? value_if_true : value_if_false
        t_max = temp_max[i] if i < len(temp_max) else None
        t_min = temp_min[i] if i < len(temp_min) else None
        prec  = precip[i]   if i < len(precip)   else 0.0
        wspd  = wind[i]     if i < len(wind)      else None

        # int() แปลง float หรือ string เป็น integer (ปัดทิ้ง decimal)
        # เหมือน parseInt() ใน JS หรือ (int) casting ใน Java
        code  = int(codes[i]) if i < len(codes) and codes[i] is not None else None

        # คำนวณ derived metrics
        # "is not None" เหมือน "!== null && !== undefined" ใน JS
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
            # .get(key, default) = ถ้าไม่มี code นั้นใน WMO_CODES → "Unknown (code)"
            "weather_summary":  WMO_CODES.get(code, f"Unknown ({code})"),
            # Boolean flags: ใช้ and เพื่อ guard None ก่อน compare
            "rain_flag":        prec is not None and prec > 0,
            "hot_flag":         t_max is not None and t_max >= HOT_THRESHOLD_C,
            "cold_flag":        t_min is not None and t_min <= COLD_THRESHOLD_C,
        })
    return rows
