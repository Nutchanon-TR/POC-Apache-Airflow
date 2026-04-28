"""
config/settings.py
==================
ไฟล์นี้เก็บค่า config ทั้งหมดของโปรเจค
DAG และ task ทุกไฟล์ import จากที่นี่ — ไม่ hardcode ค่าในโค้ด
"""

from datetime import timedelta

# ─── DAG ───────────────────────────────────────────────────────────────────
DAG_ID       = "weather_pipeline"
DAG_SCHEDULE = "0 6 * * *"   # Cron expression: "ทุกวัน เวลา 06:00 UTC"
                              # รูปแบบ: นาที  ชั่วโมง  วัน  เดือน  วันในสัปดาห์
                              #          0      6      *    *       *
DAG_TAGS     = ["weather", "poc"]

# dict คือ key-value collection ใน Python เหมือน object ใน JS หรือ Map ใน Java
# timedelta คือ class สำหรับแทน "ช่วงเวลา" เช่น 5 นาที, 2 ชั่วโมง
DAG_DEFAULT_ARGS = {
    "owner": "airflow",           # เจ้าของ DAG (แสดงใน UI)
    "depends_on_past": False,     # False = แต่ละ run ไม่ขึ้นกับ run ที่แล้ว
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,                 # ถ้า task ล้มเหลว ให้ลองใหม่กี่ครั้ง
    "retry_delay": timedelta(minutes=5),  # รอ 5 นาทีก่อน retry
}

# ─── Open-Meteo API ────────────────────────────────────────────────────────
API_URL       = "https://api.open-meteo.com/v1/forecast"
# สังเกต: ใช้ comma คั่น parameters ใน string เดียว (รูปแบบที่ API กำหนด)
API_PARAMS    = "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode"
FORECAST_DAYS = 7    # ดึงพยากรณ์ล่วงหน้า 7 วัน
API_TIMEOUT   = 30   # รอ response จาก API ไม่เกิน 30 วินาที

# ─── Cities ────────────────────────────────────────────────────────────────
# Type hint: dict[str, dict[str, float]]
# เหมือน Java: Map<String, Map<String, Double>>
# เหมือน TypeScript: Record<string, Record<string, number>>
#
# โครงสร้าง: { "ชื่อเมือง": { "lat": ละติจูด, "lon": ลองจิจูด } }
CITIES: dict[str, dict[str, float]] = {
    "Bangkok":  {"lat": 13.7563, "lon": 100.5018},
    "Tokyo":    {"lat": 35.6762, "lon": 139.6503},
    "London":   {"lat": 51.5074, "lon": -0.1278},
    "New York": {"lat": 40.7128, "lon": -74.0060},
    "Sydney":   {"lat": -33.8688, "lon": 151.2093},
}

# ─── Thresholds ────────────────────────────────────────────────────────────
HOT_THRESHOLD_C  = 35   # temp_max >= 35°C → ติด hot_flag
COLD_THRESHOLD_C = 10   # temp_min <= 10°C → ติด cold_flag

# ─── WMO Weather Codes ─────────────────────────────────────────────────────
# WMO (World Meteorological Organization) กำหนดตัวเลขแทนสภาพอากาศ
# API ส่งมาเป็นตัวเลข → เราแปลงเป็น string ที่อ่านออก
# Type hint: dict[int, str] = Map<Integer, String> ใน Java
WMO_CODES: dict[int, str] = {
    0: "Clear sky",        1: "Mainly clear",      2: "Partly cloudy",    3: "Overcast",
    45: "Fog",             48: "Rime fog",
    51: "Light drizzle",   53: "Moderate drizzle",  55: "Dense drizzle",
    61: "Slight rain",     63: "Moderate rain",     65: "Heavy rain",
    71: "Slight snow",     73: "Moderate snow",     75: "Heavy snow",
    80: "Slight showers",  81: "Moderate showers",  82: "Violent showers",
    95: "Thunderstorm",    96: "Thunderstorm + slight hail", 99: "Thunderstorm + heavy hail",
}
