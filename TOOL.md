# TOOL.md — คู่มือการใช้งาน POC-Airflow

## สารบัญ
- [Prerequisites](#prerequisites)
- [ติดตั้งและเริ่มต้น](#ติดตั้งและเริ่มต้น)
- [เข้าใช้งาน Airflow UI](#เข้าใช้งาน-airflow-ui)
- [รัน DAG](#รัน-dag)
- [ดูผลลัพธ์](#ดูผลลัพธ์)
- [คำสั่งที่ใช้บ่อย](#คำสั่งที่ใช้บ่อย)
- [Troubleshooting](#troubleshooting)
- [ปิดระบบ](#ปิดระบบ)
- [ปรับแต่ง](#ปรับแต่ง)

---

## Prerequisites

| เครื่องมือ | เวอร์ชัน | ดาวน์โหลด |
|---|---|---|
| Docker Desktop | 24.x+ | https://www.docker.com/products/docker-desktop |
| Docker Compose | v2.x+ (มาพร้อม Docker Desktop) | — |

> ต้องเปิด Docker Desktop ก่อนใช้งาน

**ทรัพยากรที่แนะนำ:**
- RAM: 2 GB ขึ้นไป (ระบบใช้ ~900 MB)
- Disk: 3 GB ว่าง (สำหรับ Docker images)

---

## ติดตั้งและเริ่มต้น

### Step 1: สร้างโฟลเดอร์ที่จำเป็น

```bash
mkdir -p logs plugins
```

### Step 2: Build Docker Image

```bash
docker compose build
```

> ครั้งแรกใช้เวลา 3-5 นาที (ดาวน์โหลด Airflow image + ติดตั้ง packages)

### Step 3: Initialize Airflow (ครั้งแรกครั้งเดียว)

```bash
docker compose up airflow-init
```

> รอจนเห็น `exited with code 0` แสดงว่าสร้าง database และ admin user สำเร็จ

### Step 4: Start ทุก Services

```bash
docker compose up -d
```

> `-d` = detached mode (รันใน background)

### Step 5: ตรวจสอบสถานะ

```bash
docker compose ps
```

Services ที่ต้องเห็น:

```
NAME                               STATUS
poc-airflow-airflow-webserver-1    Up (healthy)
poc-airflow-airflow-scheduler-1    Up (healthy)
poc-airflow-postgres-1             Up (healthy)
```

---

## เข้าใช้งาน Airflow UI

เปิดเบราว์เซอร์:

```
http://localhost:8080
```

| ช่อง | ค่า |
|---|---|
| Username | `airflow` |
| Password | `airflow` |

---

## รัน DAG

### เปิดใช้งาน DAG

1. เข้า Airflow UI → **DAGs**
2. หา DAG ชื่อ `weather_pipeline`
3. Toggle สวิตช์เปิด (Unpause DAG)

### Trigger ด้วยมือ

**ผ่าน UI:**
คลิกปุ่ม ▶ (Trigger DAG) ที่หน้า DAG list

**ผ่าน CLI:**
```bash
docker compose exec airflow-webserver airflow dags trigger weather_pipeline
```

### ดูสถานะ

คลิกชื่อ DAG → **Graph** เพื่อเห็น flow ของ tasks

สีของ task:
- **เขียวเข้ม** = สำเร็จ (success)
- **เหลือง** = กำลังรัน (running)
- **แดง** = ล้มเหลว (failed)
- **เทา** = รอคิว (queued)

---

## ดูผลลัพธ์

ผลลัพธ์ทั้งหมดแสดงใน **Airflow task log** ของ task `report`

1. คลิกชื่อ DAG → คลิก task **report** (วงกลมสีเขียว)
2. เลือก **Log**
3. ดูตาราง weather forecast ของทุกเมือง

ตัวอย่างผลลัพธ์:

```
============================================================
WEATHER FORECAST REPORT
============================================================

[Bangkok]
  Date         Summary                Max°C  Min°C  Rain mm  Flags
  ──────────────────────────────────────────────────────────────
  2025-01-01   Clear sky               36.5   24.2      0.0  HOT
  2025-01-02   Partly cloudy           34.1   23.8      2.5  RAIN
  ...

[Tokyo]
  ...

Total rows: 35
============================================================
```

---

## คำสั่งที่ใช้บ่อย

```bash
# ดูสถานะ services
docker compose ps

# ดู log แบบ real-time
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-webserver

# เข้า shell ของ Airflow container
docker compose exec airflow-webserver bash

# ตรวจสอบ DAG syntax
docker compose exec airflow-webserver python /opt/airflow/dags/weather_dag.py

# list DAGs ทั้งหมด
docker compose exec airflow-webserver airflow dags list

# trigger DAG
docker compose exec airflow-webserver airflow dags trigger weather_pipeline
```

---

## Troubleshooting

### DAG ไม่ปรากฏใน UI

```bash
# ดู error จาก scheduler
docker compose logs airflow-scheduler --tail=50

# ตรวจ syntax ของ DAG file
docker compose exec airflow-webserver python /opt/airflow/dags/weather_dag.py
```

> สาเหตุที่พบบ่อย: import error, syntax error ในไฟล์ DAG

### Task ล้มเหลว (Failed)

1. คลิก task ที่สีแดงใน UI
2. เลือก **Log** ดู error message
3. หรือดูจาก CLI:

```bash
docker compose logs airflow-scheduler --tail=100
```

### Port 8080 ถูกใช้แล้ว

แก้ไข `docker-compose.yml`:

```yaml
ports:
  - "8081:8080"   # เปลี่ยน 8080 เป็น 8081 (หรือ port อื่น)
```

### Reset ทั้งหมด

```bash
docker compose down -v           # ลบ containers + volumes
docker compose build --no-cache  # build ใหม่
docker compose up airflow-init   # initialize ใหม่
docker compose up -d
```

---

## ปิดระบบ

```bash
# หยุดชั่วคราว (เก็บข้อมูลไว้)
docker compose stop

# เริ่มใหม่หลังหยุด
docker compose start

# ปิดและลบ containers (เก็บ volumes ไว้)
docker compose down

# ปิดและลบทุกอย่างรวม volumes (ข้อมูลหาย)
docker compose down -v
```

---

## ปรับแต่ง

### เพิ่มเมือง

แก้ไข `dags/config/settings.py`:

```python
CITIES: dict[str, dict[str, float]] = {
    "Bangkok":    {"lat": 13.7563, "lon": 100.5018},
    "Chiang Mai": {"lat": 18.7883, "lon": 98.9853},   # เพิ่มใหม่
    # ...
}
```

### เปลี่ยน Schedule

แก้ไข `DAG_SCHEDULE` ใน `dags/config/settings.py`:

```python
DAG_SCHEDULE = "0 6 * * *"     # ทุกวัน 06:00 UTC
DAG_SCHEDULE = "0 */6 * * *"   # ทุก 6 ชั่วโมง
DAG_SCHEDULE = "@hourly"        # ทุกชั่วโมง
DAG_SCHEDULE = "@daily"         # ทุกวัน (เที่ยงคืน UTC)
```

### เปลี่ยนจำนวนวันพยากรณ์

แก้ไข `FORECAST_DAYS` ใน `dags/config/settings.py`:

```python
FORECAST_DAYS = 7   # เปลี่ยนเป็น 1-16 ตามที่ API รองรับ
```

### เปลี่ยน threshold HOT/COLD

แก้ไขใน `dags/config/settings.py`:

```python
HOT_THRESHOLD_C  = 35   # temp_max >= ค่านี้ → ติด HOT flag
COLD_THRESHOLD_C = 10   # temp_min <= ค่านี้ → ติด COLD flag
```
