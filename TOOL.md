# 📖 TOOL.md — คู่มือการใช้งาน POC-Airflow Weather ETL

## สารบัญ
- [ข้อกำหนดเบื้องต้น (Prerequisites)](#ข้อกำหนดเบื้องต้น-prerequisites)
- [การติดตั้งและเริ่มต้นใช้งาน](#การติดตั้งและเริ่มต้นใช้งาน)
- [การเข้าใช้งาน Airflow UI](#การเข้าใช้งาน-airflow-ui)
- [การตั้งค่า Connection](#การตั้งค่า-connection)
- [การรัน DAG](#การรัน-dag)
- [การตรวจสอบข้อมูลใน MySQL](#การตรวจสอบข้อมูลใน-mysql)
- [การแก้ไขปัญหา (Troubleshooting)](#การแก้ไขปัญหา-troubleshooting)
- [การปิดระบบ](#การปิดระบบ)
- [ปรับแต่งเพิ่มเติม](#ปรับแต่งเพิ่มเติม)

---

## ข้อกำหนดเบื้องต้น (Prerequisites)

| เครื่องมือ       | เวอร์ชันขั้นต่ำ | ดาวน์โหลด                                      |
| ---------------- | --------------- | ----------------------------------------------- |
| Docker Desktop   | 24.x+           | https://www.docker.com/products/docker-desktop   |
| Docker Compose   | v2.x+ (built-in)| มาพร้อม Docker Desktop                          |
| Git              | 2.x+            | https://git-scm.com/downloads                   |

> ⚠️ **หมายเหตุ**: ต้องเปิด Docker Desktop ก่อนเริ่มใช้งาน

### ทรัพยากรที่แนะนำ
- RAM: 4 GB ขึ้นไป (แนะนำ 8 GB)
- Disk: 5 GB ว่าง (สำหรับ Docker images)

---

## การติดตั้งและเริ่มต้นใช้งาน

### Step 1: Clone โปรเจค

```bash
git clone <repository-url>
cd POC-Airflow
```

### Step 2: สร้างโฟลเดอร์ที่จำเป็น

```bash
mkdir -p logs plugins config
```

### Step 3: Build Docker Image

```bash
docker compose build
```
> 🕐 ครั้งแรกใช้เวลาประมาณ 3-5 นาที

### Step 4: Initialize Airflow

```bash
docker compose up airflow-init
```
> รอจนเห็นข้อความ `exited with code 0` แสดงว่าเรียบร้อย

### Step 5: Start ทุก Services

```bash
docker compose up -d
```

### Step 6: ตรวจสอบสถานะ

```bash
docker compose ps
```

ต้องเห็น services ทั้งหมดเป็น `running` หรือ `healthy`:
```
NAME                      STATUS
poc-airflow-airflow-webserver-1   Up (healthy)
poc-airflow-airflow-scheduler-1   Up (healthy)
poc-airflow-airflow-worker-1      Up (healthy)
poc-airflow-airflow-triggerer-1   Up (healthy)
poc-airflow-postgres-1            Up (healthy)
poc-airflow-redis-1               Up (healthy)
poc-airflow-mysql-1               Up (healthy)
```

---

## การเข้าใช้งาน Airflow UI

เปิดเบราว์เซอร์ไปที่:

```
http://localhost:8080
```

| ช่อง     | ค่า       |
| -------- | --------- |
| Username | `airflow` |
| Password | `airflow` |

---

## การตั้งค่า Connection

### วิธีที่ 1: ใช้ Script (แนะนำ)

**Windows:**
```cmd
scripts\setup_connection.bat
```

**Linux / macOS:**
```bash
bash scripts/setup_connection.sh
```

### วิธีที่ 2: ตั้งค่าผ่าน Airflow UI

1. เข้า Airflow UI → **Admin** → **Connections**
2. กด **+** (Add a new record)
3. กรอกข้อมูล:

| ช่อง            | ค่า              |
| --------------- | ---------------- |
| Connection Id   | `mysql_weathering` |
| Connection Type | `MySQL`          |
| Host            | `mysql`          |
| Schema          | `weathering`     |
| Login           | `airflow_user`   |
| Password        | `airflow_pass`   |
| Port            | `3306`           |

4. กด **Save**

### วิธีที่ 3: ใช้ Airflow CLI

```bash
docker compose exec airflow-webserver airflow connections add \
    mysql_weathering \
    --conn-type mysql \
    --conn-host mysql \
    --conn-port 3306 \
    --conn-login airflow_user \
    --conn-password airflow_pass \
    --conn-schema weathering
```

---

## การรัน DAG

### เปิดใช้งาน DAG

1. ไปที่ Airflow UI → **DAGs**
2. หา DAG ชื่อ `weather_etl_pipeline`
3. Toggle สวิตช์เปิด (Unpause)

### Trigger DAG ด้วยมือ

**ผ่าน UI:**
1. คลิก ▶️ (Trigger DAG) ที่หน้า DAG list

**ผ่าน CLI:**
```bash
docker compose exec airflow-webserver airflow dags trigger weather_etl_pipeline
```

### ดูสถานะการรัน

1. คลิกชื่อ DAG → จะเห็น **Graph View** แสดง flow ของ tasks
2. แต่ละ task จะเปลี่ยนสี:
   - 🟢 **เขียวเข้ม** = สำเร็จ (success)
   - 🟡 **เหลือง** = กำลังรัน (running)
   - 🔴 **แดง** = ล้มเหลว (failed)
   - ⚪ **ขาว/เทา** = รอคิว (queued / no status)

### ดู Log ของแต่ละ Task

1. คลิกที่ task ใน Graph View
2. เลือก **Log** เพื่อดูรายละเอียด

---

## การตรวจสอบข้อมูลใน MySQL

### เข้า MySQL Shell

```bash
docker compose exec mysql mysql -u airflow_user -pairflow_pass weathering
```

### Query ข้อมูล

```sql
-- ดูข้อมูลที่ Transform แล้ว
SELECT city, observation_date, temp_mean_c, weather_summary, rain_flag
FROM weather_transformed
ORDER BY city, observation_date
LIMIT 20;

-- ดูข้อมูล Raw
SELECT city, fetched_at, JSON_PRETTY(raw_json) as raw
FROM weather_raw
LIMIT 5;

-- ดู ETL Log
SELECT * FROM etl_log ORDER BY created_at DESC LIMIT 10;

-- นับจำนวน rows ต่อเมือง
SELECT city, COUNT(*) as total_records
FROM weather_transformed
GROUP BY city;

-- หาวันที่อุณหภูมิสูงสุด
SELECT city, observation_date, temp_max_c
FROM weather_transformed
ORDER BY temp_max_c DESC
LIMIT 5;
```

### ออกจาก MySQL Shell

```sql
EXIT;
```

---

## การแก้ไขปัญหา (Troubleshooting)

### ปัญหา: DAG ไม่ปรากฏใน UI

```bash
# ตรวจสอบว่า DAG file ถูกต้อง
docker compose exec airflow-webserver airflow dags list

# ตรวจสอบ syntax errors
docker compose exec airflow-webserver python /opt/airflow/dags/weather_etl_dag.py
```

### ปัญหา: MySQL Connection ล้มเหลว

```bash
# ตรวจสอบว่า MySQL container ทำงานอยู่
docker compose ps mysql

# ทดสอบ connection
docker compose exec airflow-webserver airflow connections test mysql_weathering
```

### ปัญหา: Task ล้มเหลว (Failed)

1. ดู log ที่ Airflow UI → คลิก task → **Log**
2. หรือดู log ผ่าน CLI:
```bash
docker compose logs airflow-worker --tail=100
```

### ปัญหา: Port 8080 ถูกใช้แล้ว

แก้ไขไฟล์ `docker-compose.yml` เปลี่ยน port:
```yaml
ports:
  - "8081:8080"   # เปลี่ยนจาก 8080 เป็น 8081
```

### ปัญหา: ต้องการ Reset ทั้งหมด

```bash
docker compose down -v          # ลบ containers + volumes ทั้งหมด
docker compose build --no-cache  # Build image ใหม่
docker compose up airflow-init   # Initialize ใหม่
docker compose up -d             # Start ใหม่
```

---

## การปิดระบบ

### หยุดชั่วคราว (เก็บข้อมูลไว้)

```bash
docker compose stop
```

### เริ่มใหม่หลังหยุด

```bash
docker compose start
```

### ปิดทั้งหมด (เก็บ volumes)

```bash
docker compose down
```

### ปิดทั้งหมด (ลบ volumes + ข้อมูลทั้งหมด)

```bash
docker compose down -v
```

---

## ปรับแต่งเพิ่มเติม

### เพิ่มเมืองใหม่

แก้ไขไฟล์ `dags/weather_etl_dag.py` เพิ่มเมืองใน `DEFAULT_CITIES`:

```python
DEFAULT_CITIES = {
    "Bangkok":      {"lat": 13.7563, "lon": 100.5018},
    "Chiang Mai":   {"lat": 18.7883, "lon": 98.9853},   # ← เพิ่มใหม่
    # ... เมืองอื่นๆ
}
```

### เปลี่ยน Schedule

แก้ไข `schedule` ใน DAG definition:

```python
schedule="0 6 * * *",       # ทุกวัน 06:00 UTC
schedule="0 */6 * * *",     # ทุก 6 ชม.
schedule="0 0 * * 1",       # ทุกวันจันทร์
schedule="@hourly",         # ทุกชั่วโมง
```

### เปลี่ยนรหัสผ่าน MySQL

แก้ไขไฟล์ `.env` แล้วรัน:
```bash
docker compose down -v
docker compose up -d
# แล้วตั้งค่า connection ใหม่
```
