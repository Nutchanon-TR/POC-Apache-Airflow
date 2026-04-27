# 🌦️ POC-Airflow — Weather ETL Pipeline

> **Proof of Concept** สำหรับ Apache Airflow: สาธิตการเขียน DAG, สถาปัตยกรรม ETL, และการรัน pipeline บน Docker

---

## 📌 เป้าหมายของโปรเจค

โปรเจคนี้เป็น **POC (Proof of Concept)** เพื่อศึกษา Apache Airflow โดยเฉพาะ:

1. **สถาปัตยกรรม Airflow** — ส่วนประกอบต่าง ๆ ทำงานร่วมกันอย่างไร
2. **การเขียน DAG** — ออกแบบ data pipeline ด้วย Python
3. **ETL Pattern** — Extract → Transform → Load ครบวงจร
4. **Containerization** — การรัน Airflow ด้วย Docker Compose

---

## 🏗️ สถาปัตยกรรมของระบบ (System Architecture)

```
┌──────────────────────────────────────────────────────────────┐
│                        Docker Compose                        │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Airflow     │  │  Airflow    │  │  Airflow            │  │
│  │  Webserver   │  │  Scheduler  │  │  Celery Worker      │  │
│  │  :8080       │  │             │  │                     │  │
│  └──────┬───────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                 │                     │             │
│         └────────┬────────┘                     │             │
│                  │                              │             │
│         ┌────────▼────────┐         ┌───────────▼──────────┐  │
│         │   PostgreSQL    │         │       Redis          │  │
│         │  (Metadata DB)  │         │   (Celery Broker)    │  │
│         └─────────────────┘         └──────────────────────┘  │
│                                                              │
│         ┌─────────────────────────────────────────────────┐   │
│         │                MySQL 8.0                        │   │
│         │           Database: weathering                  │   │
│         │  ┌──────────────┐ ┌────────────────────────┐    │   │
│         │  │ weather_raw  │ │ weather_transformed    │    │   │
│         │  └──────────────┘ └────────────────────────┘    │   │
│         │  ┌──────────────┐                               │   │
│         │  │  etl_log     │                               │   │
│         │  └──────────────┘                               │   │
│         └─────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP (Open-Meteo API)
                          │
                ┌─────────┴──────────┐
                │  api.open-meteo.com │
                │  (Free Weather API) │
                └────────────────────┘
```

---

## 🔧 ส่วนประกอบของ Airflow (Airflow Components)

### 1. Webserver
- **หน้าที่**: ให้บริการ Web UI สำหรับจัดการและ monitor DAGs
- **เข้าถึง**: `http://localhost:8080`
- **ทำอะไร**: ดูสถานะ DAGs, trigger runs, ดู logs, จัดการ connections

### 2. Scheduler
- **หน้าที่**: ตรวจสอบว่า DAG ไหนต้องรัน เมื่อไหร่
- **ทำอะไร**: อ่าน DAG files จาก `/dags`, คำนวณ schedule, สร้าง task instances, ส่ง task ไปให้ Worker ทำงาน

### 3. Worker (Celery)
- **หน้าที่**: ทำงานจริง (execute tasks)
- **ทำอะไร**: รับ tasks จาก Redis queue, รัน Python code, รายงานผลกลับ
- **Executor**: ใช้ `CeleryExecutor` เพื่อรองรับการรัน tasks แบบ parallel

### 4. Triggerer
- **หน้าที่**: จัดการ deferred tasks (async triggers)
- **ทำอะไร**: รัน triggers ที่ไม่ต้องคอย worker ตลอดเวลา

### 5. PostgreSQL (Metadata Database)
- **หน้าที่**: เก็บ metadata ของ Airflow (DAG runs, task instances, connections, variables)
- **ไม่ใช่**: ที่เก็บข้อมูลของเรา — เราใช้ MySQL แยกต่างหาก

### 6. Redis (Message Broker)
- **หน้าที่**: เป็น message queue สำหรับ CeleryExecutor
- **ทำอะไร**: รับ tasks จาก Scheduler แล้วส่งให้ Worker

### 7. MySQL (Target Database)
- **หน้าที่**: ที่เก็บข้อมูลสภาพอากาศ (เป้าหมายของ ETL pipeline)
- **Database**: `weathering`
- **ไม่ได้**: เป็นส่วนของ Airflow — เป็น external system ที่ pipeline เขียนข้อมูลลงไป

---

## 📊 Data Pipeline — DAG: `weather_etl_pipeline`

### ภาพรวม Flow

```
              ┌──────────────────────────┐
              │        extract           │
              │  (Fetch Open-Meteo API)  │
              └─────┬──────────┬─────────┘
                    │          │
           ┌────────▼───┐  ┌──▼──────────┐
           │ transform  │  │  save_raw   │
           │ (Compute   │  │ (Store JSON │
           │  metrics)  │  │  snapshot)  │
           └────────┬───┘  └─────────────┘
                    │
              ┌─────▼─────┐
              │   load    │
              │ (→ MySQL) │
              └───────────┘
```

### Task 1: `extract`

**ทำอะไร**: ดึงข้อมูลพยากรณ์อากาศ 7 วัน จาก [Open-Meteo API](https://open-meteo.com/) สำหรับ 5 เมือง

ข้อมูลที่ดึง:
| Field                  | คำอธิบาย                    |
| ---------------------- | --------------------------- |
| `temperature_2m_max`   | อุณหภูมิสูงสุด (°C)         |
| `temperature_2m_min`   | อุณหภูมิต่ำสุด (°C)          |
| `precipitation_sum`    | ปริมาณฝนรวม (mm)            |
| `windspeed_10m_max`    | ความเร็วลมสูงสุด (km/h)     |
| `weathercode`          | รหัสสภาพอากาศ (WMO standard) |

เมืองที่ดึง (default):
- 🇹🇭 Bangkok
- 🇯🇵 Tokyo
- 🇬🇧 London
- 🇺🇸 New York
- 🇦🇺 Sydney

### Task 2: `transform`

**ทำอะไร**: แปลงข้อมูลดิบเป็นข้อมูลที่พร้อมใช้ โดยคำนวณ:

| Metric           | สูตร / ตรรกะ                          |
| ---------------- | ------------------------------------- |
| `temp_mean_c`    | `(temp_max + temp_min) / 2`           |
| `temp_range_c`   | `temp_max - temp_min`                 |
| `weather_summary`| แปลง WMO code → ข้อความ (เช่น "Partly cloudy") |
| `rain_flag`      | `TRUE` ถ้า precipitation > 0          |
| `hot_flag`       | `TRUE` ถ้า temp_max ≥ 35°C            |
| `cold_flag`      | `TRUE` ถ้า temp_min ≤ 10°C            |

### Task 3: `load`

**ทำอะไร**: นำข้อมูลที่ transform แล้วเขียนลง MySQL

- ใช้ `INSERT ... ON DUPLICATE KEY UPDATE` (upsert)
- บันทึก log ลง table `etl_log`
- ใช้ `MySqlHook` ของ Airflow เพื่อจัดการ connection

### Task 4: `save_raw`

**ทำอะไร**: เก็บ raw JSON response ลง `weather_raw` table เพื่อ auditing

---

## 🗄️ Database Schema: `weathering`

### Table: `weather_transformed`

| Column             | Type          | คำอธิบาย                |
| ------------------ | ------------- | ----------------------- |
| id                 | BIGINT (PK)   | Auto-increment          |
| city               | VARCHAR(100)  | ชื่อเมือง               |
| latitude           | DECIMAL(8,4)  | ละติจูด                 |
| longitude          | DECIMAL(8,4)  | ลองจิจูด                |
| observation_date   | DATE          | วันที่พยากรณ์            |
| temp_max_c         | DECIMAL(5,2)  | อุณหภูมิสูงสุด (°C)      |
| temp_min_c         | DECIMAL(5,2)  | อุณหภูมิต่ำสุด (°C)       |
| temp_mean_c        | DECIMAL(5,2)  | อุณหภูมิเฉลี่ย (°C)      |
| temp_range_c       | DECIMAL(5,2)  | ช่วงอุณหภูมิ (°C)        |
| precipitation_mm   | DECIMAL(7,2)  | ปริมาณฝน (mm)           |
| windspeed_max_kmh  | DECIMAL(6,2)  | ความเร็วลมสูงสุด (km/h)  |
| weather_summary    | VARCHAR(255)  | สรุปสภาพอากาศ           |
| rain_flag          | BOOLEAN       | มีฝนตกหรือไม่            |
| hot_flag           | BOOLEAN       | อากาศร้อน (≥35°C)        |
| cold_flag          | BOOLEAN       | อากาศหนาว (≤10°C)       |
| fetched_at         | DATETIME      | เวลาที่ดึงข้อมูล          |
| created_at         | TIMESTAMP     | เวลาที่สร้าง record       |

**Unique Key**: `(city, observation_date)` — ป้องกันข้อมูลซ้ำ

### Table: `weather_raw`

เก็บ raw JSON response เต็ม ๆ จาก API เพื่อ auditing/debugging

### Table: `etl_log`

บันทึก log ของการรัน ETL แต่ละครั้ง (dag_id, run_id, status, rows_affected)

---

## 📁 โครงสร้างโปรเจค (Project Structure)

```
POC-Airflow/
├── 📄 docker-compose.yml          # รวม services ทั้งหมด
├── 📄 Dockerfile                  # Custom Airflow image + dependencies
├── 📄 requirements.txt            # Python packages เพิ่มเติม
├── 📄 .env                        # Environment variables
├── 📄 .gitignore
├── 📄 README.md                   # ← ไฟล์นี้ (อธิบายการทำงาน)
├── 📄 TOOL.md                     # คู่มือการใช้งาน (How-to guide)
│
├── 📂 dags/                       # ── Airflow DAGs & modules ──
│   ├── weather_etl_dag.py         # DAG definition (orchestration only)
│   │
│   ├── 📂 config/                 # ── Configuration ──
│   │   ├── __init__.py
│   │   └── settings.py            # Constants, city list, WMO codes, thresholds
│   │
│   ├── 📂 tasks/                  # ── Task callables (business logic) ──
│   │   ├── __init__.py
│   │   ├── extract.py             # E: Fetch data from Open-Meteo API
│   │   ├── transform.py           # T: Compute derived metrics with pandas
│   │   └── load.py                # L: Upsert to MySQL + save raw audit data
│   │
│   └── 📂 utils/                  # ── Shared utilities ──
│       ├── __init__.py
│       └── db_logger.py           # ETL audit logging to etl_log table
│
├── 📂 init-sql/                   # MySQL initial schema
│   └── init.sql                   # สร้างตาราง weather_raw, weather_transformed, etl_log
│
├── 📂 scripts/                    # Helper scripts
│   ├── setup_connection.sh        # สร้าง Airflow connection (Linux/Mac)
│   └── setup_connection.bat       # สร้าง Airflow connection (Windows)
│
├── 📂 plugins/                    # Airflow custom plugins (ว่าง — สำหรับต่อยอด)
├── 📂 config/                     # Airflow config overrides (ว่าง — สำหรับต่อยอด)
└── 📂 logs/                       # Airflow logs (auto-generated)
```

### 🧩 โครงสร้าง DAG (Clean Architecture)

โปรเจคนี้แยก code ตามหลัก **Separation of Concerns**:

```
                    weather_etl_dag.py
                    ┌────────────────┐
                    │  Orchestration │  ← DAG definition + task wiring
                    │   Layer        │    (ไม่มี business logic)
                    └───────┬────────┘
                            │ imports
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌───────────┐     ┌─────────────┐     ┌────────────┐
  │  extract  │     │  transform  │     │    load     │
  │  .py      │     │  .py        │     │    .py      │  ← Business Logic
  └─────┬─────┘     └──────┬──────┘     └─────┬──────┘    (แต่ละไฟล์ = 1 task)
        │                  │                  │
        ▼                  ▼                  ▼
  ┌──────────┐     ┌─────────────┐     ┌────────────┐
  │ settings │     │  settings   │     │ db_logger  │  ← Shared Modules
  │ .py      │     │  .py        │     │ .py        │    (config + utilities)
  └──────────┘     └─────────────┘     └────────────┘
```

| Layer          | ไฟล์                    | หน้าที่                                           |
| -------------- | ----------------------- | ------------------------------------------------- |
| Orchestration  | `weather_etl_dag.py`    | นิยาม DAG, สร้าง tasks, กำหนด dependency          |
| Business Logic | `tasks/extract.py`      | ดึงข้อมูลจาก API                                   |
|                | `tasks/transform.py`    | แปลงข้อมูล, คำนวณ metrics                          |
|                | `tasks/load.py`         | เขียนลง MySQL (transformed + raw)                  |
| Configuration  | `config/settings.py`    | ค่าคงที่, city list, WMO codes, thresholds         |
| Utilities      | `utils/db_logger.py`    | บันทึก ETL log ลง database                        |

---

## 🔑 Core Concepts ที่เรียนรู้จากโปรเจคนี้

### 1. DAG (Directed Acyclic Graph)
- DAG คือ "แผนผัง" ของ pipeline ที่กำหนดว่า tasks ไหนทำก่อน-หลัง
- เขียนด้วย Python ในไฟล์ `.py` แล้ววางในโฟลเดอร์ `dags/`
- ตัวอย่าง dependency: `extract >> [transform, save_raw]` → `transform >> load`

### 2. Operators
- **PythonOperator**: รัน Python function — ใช้ได้หลากหลายที่สุด
- **MySqlOperator**: รัน SQL ตรง ๆ บน MySQL (ไม่ได้ใช้ในโปรเจคนี้ แต่มีใน Airflow providers)

### 3. Hooks
- **MySqlHook**: จัดการ connection กับ MySQL Database
- Hooks จะอ่าน connection details จาก Airflow Connections (UI/CLI)

### 4. XCom (Cross-Communication)
- วิธีส่งข้อมูลระหว่าง tasks
- `ti.xcom_push(key, value)` → `ti.xcom_pull(key, task_ids)`
- ⚠️ ไม่ควรส่งข้อมูลขนาดใหญ่มาก (>48KB) ผ่าน XCom

### 5. Connections
- Airflow เก็บ credentials (host, port, user, password) แบบ centralized
- ตั้งค่าผ่าน UI, CLI, หรือ environment variables
- DAG ใช้ `conn_id` อ้างอิง ไม่ hard-code credentials

### 6. Executor
- **CeleryExecutor**: กระจาย tasks ไปหลาย workers (ผ่าน Redis)
- เหมาะสำหรับ production — scale out ได้
- ตัวอื่น: `LocalExecutor` (single-node), `KubernetesExecutor` (K8s pods)

---

## 🚀 Quick Start

```bash
# 1. สร้างโฟลเดอร์
mkdir -p logs plugins config

# 2. Build & Init
docker compose build
docker compose up airflow-init

# 3. Start
docker compose up -d

# 4. Setup connection
scripts\setup_connection.bat        # Windows
# bash scripts/setup_connection.sh  # Linux/Mac

# 5. เปิด browser → http://localhost:8080
# Login: airflow / airflow
# เปิด DAG → Trigger → ดูผลลัพธ์!
```

---

## 📝 หมายเหตุ

- API ที่ใช้: [Open-Meteo](https://open-meteo.com/) — ฟรี, ไม่ต้อง API key
- Airflow metadata ใช้ PostgreSQL (แยกจาก MySQL target)
- ข้อมูลจะถูก upsert (update หรือ insert) ตาม unique key `(city, observation_date)`
- Schedule default คือทุกวันเวลา 06:00 UTC

---

## 📚 เอกสารอ้างอิง

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Open-Meteo API Documentation](https://open-meteo.com/en/docs)
- [Airflow MySQL Provider](https://airflow.apache.org/docs/apache-airflow-providers-mysql/stable/index.html)
- [Docker Compose for Airflow](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
