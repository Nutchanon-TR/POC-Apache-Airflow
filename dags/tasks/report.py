"""
tasks/report.py
===============
REPORT — แสดงผลข้อมูลพยากรณ์อากาศใน Airflow task log

Input:  XCom["transformed_weather"]  (จาก transform task)
Output: ตาราง log ที่ดูได้ใน Airflow UI → คลิก task "report" → Logs

ไม่มี external dependencies — ใช้แค่ Python standard library
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


# ─── Main Function ──────────────────────────────────────────────────────────

def report_weather(**context) -> int:
    """Print ข้อมูลพยากรณ์อากาศทุกเมืองแบบตาราง ออก Airflow log"""

    rows: list[dict] = json.loads(
        context["ti"].xcom_pull(key="transformed_weather", task_ids="transform")
    )

    # จัดกลุ่มข้อมูลตามเมือง
    # setdefault(key, default) = ถ้ายังไม่มี key นี้ ให้สร้างเป็น default ก่อน แล้วคืนค่า
    # เหมือน JS: by_city[row.city] = by_city[row.city] ?? []
    by_city: dict[str, list[dict]] = {}
    for row in rows:
        by_city.setdefault(row["city"], []).append(row)

    logger.info("=" * 60)
    logger.info("WEATHER FORECAST REPORT")
    logger.info("=" * 60)

    for city, forecasts in by_city.items():
        logger.info("\n[%s]", city)

        # %-12s, %6s คือ format string แบบเก่า (คล้าย printf ใน C/Java)
        # %-12s = ชิดซ้าย ความกว้าง 12 ตัวอักษร
        # %6s   = ชิดขวา ความกว้าง 6 ตัวอักษร
        logger.info("  %-12s %-22s %6s %6s %8s %s", "Date", "Summary", "Max°C", "Min°C", "Rain mm", "Flags")
        logger.info("  " + "-" * 70)

        for f in forecasts:
            # filter(None, [...]) = กรอง falsy values ออก (None, "", 0, False)
            # เหมือน JS: ["HOT", "", "RAIN"].filter(Boolean)
            # " ".join([...]) = เชื่อม list เป็น string ด้วยช่องว่าง
            # เหมือน JS: [...].join(" ")
            flags = " ".join(filter(None, [
                "HOT"  if f["hot_flag"]  else "",
                "COLD" if f["cold_flag"] else "",
                "RAIN" if f["rain_flag"] else "",
            ])) or "-"   # "or '-'" = ถ้า flags เป็น "" (empty string = falsy) ให้ใช้ "-" แทน

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
