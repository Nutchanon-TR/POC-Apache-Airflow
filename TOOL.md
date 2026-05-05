# TOOL.md - คู่มือการใช้งาน POC-Airflow

คู่มือนี้อิงจากโค้ดปัจจุบันใน repo:

- DAG files อยู่ใน `WeatherDag/`
- Airflow container mount `./WeatherDag` ไปที่ `/opt/airflow/dags`
- DAG ID ที่ใช้จริงคือ `weather_ingest` และ `weather_report`

## Prerequisites

| เครื่องมือ | เวอร์ชันแนะนำ |
|---|---|
| Docker Desktop | 24.x ขึ้นไป |
| Docker Compose | v2.x ขึ้นไป |

ต้องตั้งค่า Supabase credentials ก่อนรัน:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

## ติดตั้งและเริ่มต้น

```bash
# สร้างโฟลเดอร์ runtime
mkdir -p logs plugins

# build Airflow image
docker compose build

# initialize Airflow DB และสร้าง user
docker compose up airflow-init

# start services
docker compose up -d
```

ตรวจสอบสถานะ:

```bash
docker compose ps
```

Services หลักที่ควรเห็น:

```text
poc-airflow-airflow-webserver-1
poc-airflow-airflow-scheduler-1
poc-airflow-mysql-1
```

## เข้าใช้งาน Airflow UI

เปิด:

```text
http://localhost:8080
```

| ช่อง | ค่า default |
|---|---|
| Username | `airflow` |
| Password | `airflow` |

## เปิดและรัน DAG

### เปิดใช้งาน DAG

1. เข้า Airflow UI -> **DAGs**
2. หา `weather_ingest` และ `weather_report`
3. Toggle unpause DAG ที่ต้องการใช้งาน

### Trigger `weather_ingest` ผ่าน UI

1. กดปุ่ม Trigger ที่ DAG `weather_ingest`
2. ใส่ config ได้ เช่น:

```json
{
  "forecast_days": 7,
  "cities": ["Bangkok", "Tokyo", "London", "New York", "Sydney"],
  "trigger_report": true
}
```

ถ้า `trigger_report=true`, หลัง load เข้า Supabase สำเร็จ DAG จะ trigger `weather_report` ต่อโดยส่ง `run_date` เป็น `{{ ds }}`

### Trigger `weather_report` ผ่าน UI

ใช้เมื่อต้องการอ่านข้อมูลจาก Supabase แล้ว report เฉพาะวันที่:

```json
{
  "run_date": "2026-05-04"
}
```

ถ้าไม่ใส่ `run_date` หรือใส่เป็นค่าว่าง DAG จะใช้วันที่ปัจจุบันของ runtime

## CLI Commands

List DAGs:

```bash
docker compose exec airflow-webserver airflow dags list
```

Trigger `weather_ingest`:

```bash
docker compose exec airflow-webserver airflow dags trigger weather_ingest
```

Trigger `weather_ingest` พร้อม conf:

```bash
docker compose exec airflow-webserver airflow dags trigger weather_ingest --conf '{"forecast_days": 3, "cities": ["Bangkok", "Tokyo"], "trigger_report": true}'
```

Trigger `weather_report` พร้อม `run_date`:

```bash
docker compose exec airflow-webserver airflow dags trigger weather_report --conf '{"run_date": "2026-05-04"}'
```

ตรวจสอบ DAG import/syntax ใน container:

```bash
docker compose exec airflow-webserver python /opt/airflow/dags/dag_ingest.py
docker compose exec airflow-webserver python /opt/airflow/dags/dag_report.py
```

ดู logs:

```bash
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-webserver
```

เข้า shell container:

```bash
docker compose exec airflow-webserver bash
```

## ดูผลลัพธ์

### ผลของ `weather_ingest`

เปิด DAG `weather_ingest` -> **Graph** แล้วดู logs ของแต่ละ task:

- `extract_weather`: จำนวนเมืองที่ดึงจาก Open-Meteo
- `transform_weather`: จำนวน rows ที่แปลงได้
- `load_weather`: จำนวน rows ที่ insert เข้า Supabase
- `should_trigger`: เช็คค่า `trigger_report`
- `trigger_report_dag`: trigger DAG `weather_report`

### ผลของ `weather_report`

เปิด DAG `weather_report` -> **Graph** -> task `report_weather` -> **Log**

ตัวอย่าง output:

```text
============================================================
WEATHER FORECAST REPORT
============================================================

[Bangkok]
  Date         Summary                Max°C  Min°C  Rain mm  Flags
  ----------------------------------------------------------------------
  2026-05-04   Clear sky               36.5   24.2      0.0  HOT
  2026-05-05   Partly cloudy           34.1   23.8      2.5  RAIN

Total rows: 10
============================================================
```

## ปรับแต่ง

### เพิ่มหรือแก้เมือง

แก้ไข `WeatherDag/config.py`:

```python
CITIES: dict[str, dict[str, float]] = {
    "Bangkok": {"lat": 13.7563, "lon": 100.5018},
    "Chiang Mai": {"lat": 18.7883, "lon": 98.9853},
}
```

### เปลี่ยนจำนวนวันพยากรณ์

ตั้งค่าตอน trigger ด้วย param `forecast_days`:

```json
{
  "forecast_days": 3
}
```

ค่าที่รองรับใน DAG คือ `1` ถึง `16`

### เปลี่ยนเมืองตอน trigger

```json
{
  "cities": ["Bangkok", "Sydney"]
}
```

ถ้าส่งชื่อเมืองที่ไม่มีใน `CITIES` เมืองนั้นจะถูกกรองออก และถ้าไม่เหลือเมืองที่ถูกต้อง task `extract_weather` จะ fail

### เปิด/ปิดการ trigger report ต่อ

```json
{
  "trigger_report": false
}
```

เมื่อเป็น `false`, `should_trigger` จะ short-circuit และ skip `trigger_report_dag`

### เปลี่ยน schedule

แก้ค่า `schedule` ในไฟล์ DAG โดยตรง:

- `WeatherDag/dag_ingest.py`: `schedule="0 6 * * *"`
- `WeatherDag/dag_report.py`: `schedule="30 6 * * *"`

## Troubleshooting

### DAG ไม่ปรากฏใน UI

ตรวจ logs:

```bash
docker compose logs airflow-scheduler --tail=100
```

ตรวจ import/syntax:

```bash
docker compose exec airflow-webserver python /opt/airflow/dags/dag_ingest.py
docker compose exec airflow-webserver python /opt/airflow/dags/dag_report.py
```

สาเหตุที่พบบ่อย:

- `.env` ไม่มี `SUPABASE_URL` หรือ `SUPABASE_KEY`
- import error จาก dependency
- syntax error ในไฟล์ DAG

### `weather_report` ไม่เจอข้อมูล

`fetch_from_supabase` filter ด้วย:

```text
dag_run_date=eq.{run_date}
```

ตรวจว่า Supabase table `weather` มีคอลัมน์ `dag_run_date` และค่าตรงกับ `run_date` ที่ trigger หรือไม่

### Port 8080 ถูกใช้แล้ว

แก้ `docker-compose.yml`:

```yaml
ports:
  - "8081:8080"
```

จากนั้นเปิด `http://localhost:8081`

### Reset ระบบ

คำสั่งนี้ลบ containers และ volumes:

```bash
docker compose down -v
docker compose build --no-cache
docker compose up airflow-init
docker compose up -d
```

## ปิดระบบ

หยุดชั่วคราว:

```bash
docker compose stop
```

เริ่มใหม่:

```bash
docker compose start
```

ปิด containers แต่เก็บ volumes:

```bash
docker compose down
```
