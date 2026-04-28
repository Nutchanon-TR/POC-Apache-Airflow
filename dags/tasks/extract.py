"""
tasks/extract.py
================
EXTRACT — ดึงข้อมูลพยากรณ์อากาศ 7 วันจาก Open-Meteo API

Input:  ไม่มี (ดึงจาก API โดยตรง)
Output: push raw JSON ลง XCom ด้วย key "raw_weather"
"""

# from __future__ import annotations ช่วยให้ type hints ทำงานได้ใน Python เวอร์ชันเก่า
from __future__ import annotations

import json      # สำหรับแปลง Python object ↔ JSON string
import logging   # สำหรับ print log (ใช้แทน print() ใน production code)

import requests  # library สำหรับเรียก HTTP (ต้องติดตั้งเพิ่ม — ดู requirements.txt)

# import ค่า config จาก settings.py (ไม่ hardcode ใน task)
from config.settings import API_PARAMS, API_TIMEOUT, API_URL, CITIES, FORECAST_DAYS

# logging.getLogger(__name__)
# __name__ คือ magic variable ใน Python = ชื่อ module ปัจจุบัน
# เหมือน Java: Logger.getLogger(ExtractTask.class.getName())
# ทำให้ log แสดงชื่อไฟล์ที่ log ออกมา เช่น "[tasks.extract] Fetching Bangkok..."
logger = logging.getLogger(__name__)


# ─── Main Function ──────────────────────────────────────────────────────────

# "-> int" คือ return type hint บอกว่า function นี้ return int
# เหมือน Java: public int extractWeather(...)
# Python ไม่บังคับใส่ แต่ช่วย IDE และ linter จับ error ได้
def extract_weather(**context) -> int:
    """ดึงพยากรณ์อากาศทุกเมืองแล้ว push ลง XCom"""

    # **context คือ "keyword arguments" ที่ Airflow ส่งเข้ามาให้อัตโนมัติ
    # ** (double asterisk) หมายถึง "unpack dict เป็น keyword args"
    # เทียบ JS: function extractWeather({ ti, dag, run_id, ...rest })
    # context มี key สำคัญเช่น:
    #   context["ti"]           = Task Instance (object ของ task นี้)
    #   context["logical_date"] = วันที่ที่ DAG กำลัง run
    #   context["run_id"]       = ID ของ DAG run นี้

    # list[dict] = type hint บอกว่า all_raw เป็น list ของ dict
    # เหมือน Java: List<Map<String, Object>>
    # เหมือน TypeScript: Array<Record<string, any>>
    all_raw: list[dict] = []

    # .items() คืนคู่ (key, value) จาก dict
    # เทียบ JS: Object.entries(CITIES) → [[city, coords], ...]
    # for city, coords in ... = destructuring ใน for loop
    # เทียบ JS: for (const [city, coords] of Object.entries(CITIES))
    for city, coords in CITIES.items():

        # f"..." คือ f-string = string interpolation
        # เทียบ JS template literal: `${API_URL}?latitude=${coords['lat']}...`
        url = (
            f"{API_URL}"
            f"?latitude={coords['lat']}&longitude={coords['lon']}"
            f"&daily={API_PARAMS}"
            f"&timezone=auto&forecast_days={FORECAST_DAYS}"
        )
        logger.info("Fetching %s ...", city)

        # requests.get() ส่ง HTTP GET request ไปยัง url
        # timeout=API_TIMEOUT = รอไม่เกิน 30 วินาที ถ้าเกินจะ raise exception
        response = requests.get(url, timeout=API_TIMEOUT)

        # raise_for_status() จะ raise HTTPError ถ้า status code เป็น 4xx หรือ 5xx
        # เหมือน Java: if (!response.isSuccessful()) throw new HttpException(...)
        response.raise_for_status()

        # เพิ่ม dict เข้า list ด้วย .append()
        # เทียบ JS: all_raw.push({ city, latitude: ..., raw_json: ... })
        all_raw.append({
            "city":      city,
            "latitude":  coords["lat"],
            "longitude": coords["lon"],
            "raw_json":  response.json(),  # แปลง JSON response เป็น Python dict
        })
        logger.info("  ✓ %s — %d days", city, len(response.json().get("daily", {}).get("time", [])))

    # XCom (Cross-Communication) คือกลไกของ Airflow สำหรับส่งข้อมูลระหว่าง tasks
    # context["ti"] = Task Instance object
    # xcom_push(key, value) = เก็บข้อมูลไว้ให้ task อื่นดึงได้
    # json.dumps() = แปลง Python list/dict → JSON string
    context["ti"].xcom_push(key="raw_weather", value=json.dumps(all_raw))

    logger.info("Extract complete — %d cities", len(all_raw))

    # return จำนวนเมืองที่ดึงสำเร็จ (Airflow เก็บค่านี้ไว้ใน XCom อัตโนมัติด้วย)
    return len(all_raw)
