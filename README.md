# POC-Airflow — Weather Pipeline

> **Proof of Concept** สำหรับ Apache Airflow: สาธิตการเขียน DAG และการรัน pipeline บน Docker

---

## เป้าหมายของโปรเจค

โปรเจคนี้เป็น **POC (Proof of Concept)** เพื่อศึกษา Apache Airflow โดยเฉพาะ:

1. **สถาปัตยกรรม Airflow** — ส่วนประกอบต่าง ๆ ทำงานร่วมกันอย่างไร
2. **การเขียน DAG** — ออกแบบ data pipeline ด้วย Python
3. **ETL Pattern** — Extract → Transform → Report
4. **Containerization** — การรัน Airflow ด้วย Docker Compose

---

## สถาปัตยกรรมของระบบ

```
┌────────────────────────────────────────────────────────┐
│                     Docker Compose                     │
│                                                        │
│  ┌─────────────────┐       ┌──────────────────────┐   │
│  │ Airflow          │       │ Airflow              │   │
│  │ Webserver  :8080 │       │ Scheduler            │   │
│  │ (UI / API)       │       │ (ตรวจ schedule)      │   │
│  └────────┬─────────┘       └──────────┬───────────┘   │
│           │                            │               │
│           └────────────┬───────────────┘               │
│                        │                               │
│               ┌────────▼────────┐                      │
│               │   PostgreSQL    │                      │
│               │  (Metadata DB)  │                      │
│               └─────────────────┘                      │
└────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP GET
                          │
               ┌──────────┴──────────┐
               │  api.open-meteo.com │
               │  (Free Weather API) │
               └─────────────────────┘
```

### ส่วนประกอบ (Services)

| Service | หน้าที่ | RAM (ประมาณ) |
|---|---|---|
| **airflow-webserver** | Web UI สำหรับดู DAGs, trigger runs, ดู logs | ~500 MB |
| **airflow-scheduler** | ตรวจว่า DAG ไหนถึงเวลารัน สร้าง task instances | ~300 MB |
| **postgres** | เก็บ metadata ของ Airflow (DAG runs, task states, logs) | ~100 MB |

> รวมทั้งหมด ~900 MB — ใช้ได้สบายบน VM 4 GB

### Executor: LocalExecutor

โปรเจคนี้ใช้ **LocalExecutor** ซึ่งรัน tasks ใน process เดียวกับ Scheduler  
ไม่ต้องการ Redis หรือ Celery Worker → เหมาะกับ development และ POC

| Executor | ใช้เมื่อ | ต้องการ |
|---|---|---|
| **LocalExecutor** | dev, POC, single node | แค่ PostgreSQL |
| CeleryExecutor | production, หลาย worker | + Redis + Worker |
| KubernetesExecutor | scale บน K8s | + Kubernetes cluster |

---

## Data Pipeline — DAG: `weather_pipeline`

### Flow

```
extract ──→ transform ──→ report
```

### Task 1: `extract`

ดึงข้อมูลพยากรณ์อากาศ 7 วันจาก [Open-Meteo API](https://open-meteo.com/) สำหรับ 5 เมือง

| Field | คำอธิบาย |
|---|---|
| `temperature_2m_max` | อุณหภูมิสูงสุด (°C) |
| `temperature_2m_min` | อุณหภูมิต่ำสุด (°C) |
| `precipitation_sum` | ปริมาณฝนรวม (mm) |
| `windspeed_10m_max` | ความเร็วลมสูงสุด (km/h) |
| `weathercode` | รหัสสภาพอากาศ (WMO standard) |

เมืองที่ดึง: Bangkok, Tokyo, London, New York, Sydney

### Task 2: `transform`

แปลงข้อมูลดิบเป็นข้อมูลที่พร้อมใช้

| Output field | สูตร |
|---|---|
| `temp_mean_c` | `(temp_max + temp_min) / 2` |
| `temp_range_c` | `temp_max - temp_min` |
| `weather_summary` | แปลง WMO code → ข้อความ (เช่น "Partly cloudy") |
| `rain_flag` | `True` ถ้า precipitation > 0 |
| `hot_flag` | `True` ถ้า temp_max ≥ 35°C |
| `cold_flag` | `True` ถ้า temp_min ≤ 10°C |

### Task 3: `report`

Print ผลลัพธ์แบบตารางออก Airflow task log — ดูได้ใน UI → คลิก task → Logs

```
[Bangkok]
  Date         Summary                Max°C  Min°C  Rain mm  Flags
  ─────────────────────────────────────────────────────────────────
  2025-01-01   Clear sky               36.5   24.2      0.0  HOT
  2025-01-02   Partly cloudy           34.1   23.8      2.5  RAIN
```

---

## โครงสร้างโปรเจค

```
POC-Airflow/
├── docker-compose.yml        # กำหนด services ทั้งหมด (postgres, webserver, scheduler)
├── Dockerfile                # สร้าง custom Airflow image
├── requirements.txt          # Python packages เพิ่มเติม
├── .env                      # Environment variables (credentials)
│
└── dags/                     # ── Airflow DAGs ──────────────────────────
    ├── weather_dag.py         # DAG definition (orchestration only)
    │
    ├── config/               # ── Configuration ──────────────────────
    │   └── settings.py       # ค่าคงที่ทั้งหมด: cities, API URL, thresholds
    │
    └── tasks/                # ── Business Logic ──────────────────────
        ├── extract.py        # E: ดึงข้อมูลจาก Open-Meteo API
        ├── transform.py      # T: คำนวณ metrics, ติด flags
        └── report.py         # R: แสดงผลใน Airflow log
```

### Clean Architecture

```
                  weather_dag.py
               ┌────────────────┐
               │  Orchestration │  ← นิยาม DAG + task dependencies
               │  Layer only    │    ไม่มี business logic
               └───────┬────────┘
                       │ imports
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ extract  │ │transform │ │  report  │  ← Business Logic
    └────┬─────┘ └────┬─────┘ └────┬─────┘    (1 ไฟล์ = 1 task)
         │            │            │
         └────────────┴────────────┘
                      │ imports
               ┌──────▼──────┐
               │ settings.py │  ← Config (single source of truth)
               └─────────────┘
```

---

## Airflow Concepts ที่ใช้ในโปรเจคนี้

### DAG (Directed Acyclic Graph)
- "แผนผัง" ของ pipeline กำหนดว่า tasks ไหนทำก่อน-หลัง
- เขียนด้วย Python วางในโฟลเดอร์ `dags/`
- `extract >> transform >> report` = ลำดับการทำงาน

### Operators
- **PythonOperator**: รัน Python function — ใช้บ่อยที่สุด
- ตัวอื่นที่มีใน Airflow: `BashOperator`, `HttpOperator`, `EmailOperator`, ...

### XCom (Cross-Communication)
- วิธีส่งข้อมูลระหว่าง tasks
- `ti.xcom_push(key, value)` → เก็บข้อมูล
- `ti.xcom_pull(key, task_ids)` → ดึงข้อมูล
- ไม่ควรส่งข้อมูลขนาดใหญ่ผ่าน XCom (เหมาะกับ metadata หรือ JSON ขนาดเล็ก)

### Schedule (Cron Expression)
```
"0 6 * * *"
 │ │ │ │ └─ วันในสัปดาห์ (0=อาทิตย์)
 │ │ │ └─── เดือน
 │ │ └───── วันที่
 │ └─────── ชั่วโมง
 └───────── นาที
```

---

## Quick Start

```bash
# 1. สร้างโฟลเดอร์
mkdir -p logs plugins

# 2. Build image
docker compose build

# 3. Initialize Airflow (ครั้งแรกครั้งเดียว)
docker compose up airflow-init

# 4. Start
docker compose up -d

# 5. เปิด browser → http://localhost:8080
# Login: airflow / airflow
# เปิด DAG weather_pipeline → Trigger → ดูผลที่ task report → Logs
```

---

## เอกสารอ้างอิง

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Open-Meteo API Documentation](https://open-meteo.com/en/docs)
- [Docker Compose for Airflow](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
