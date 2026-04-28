"""
weather_dag.py
==============
Airflow DAG — Weather Pipeline (POC)

ไฟล์นี้คือ "orchestration layer" เท่านั้น
หน้าที่: นิยาม DAG, สร้าง tasks, กำหนดลำดับการทำงาน
ห้ามมี business logic ในไฟล์นี้ → ดูในโฟลเดอร์ tasks/ แทน

Pipeline:
    extract → transform → report

Schedule: ทุกวัน 06:00 UTC
"""

# from __future__ import annotations
# ─────────────────────────────────────────────────────────────────────────────
# บรรทัดนี้บอก Python ให้ประมวลผล type hints แบบ "lazy"
# ทำให้ใช้ syntax type hint สมัยใหม่ได้ในทุก Python version
# (ถ้าไม่ใส่ Python เวอร์ชันเก่าบางตัวอาจ error กับ type hint ที่ซับซ้อน)
from __future__ import annotations

from datetime import datetime

# import คือการเอา code จากไฟล์อื่นมาใช้ เหมือน import/require ใน JS
# หรือ import ใน Java
from airflow import DAG
from airflow.operators.python import PythonOperator

# import จาก module ภายในโปรเจค (config/ และ tasks/)
from config.settings import DAG_DEFAULT_ARGS, DAG_ID, DAG_SCHEDULE, DAG_TAGS
from tasks.extract import extract_weather
from tasks.transform import transform_weather
from tasks.report import report_weather

# ─── DAG Definition ────────────────────────────────────────────────────────
#
# "with ... as dag:" คือ Context Manager ใน Python
# เหมือน try-with-resources ใน Java
# ทุก operator ที่สร้างภายใน block นี้จะถูก register เข้า DAG อัตโนมัติ
#
# DAG (Directed Acyclic Graph) คือ "แผนผัง" ของ pipeline
# กำหนดว่ามี tasks อะไรบ้าง และทำงานลำดับไหน
with DAG(
    dag_id=DAG_ID,                  # ชื่อ DAG ที่แสดงใน Airflow UI
    default_args=DAG_DEFAULT_ARGS,  # ค่า default เช่น retry, owner
    description="Weather pipeline: Open-Meteo API → Transform → Report",
    schedule=DAG_SCHEDULE,          # cron expression — เมื่อไหร่ให้รัน
    start_date=datetime(2025, 1, 1),# Airflow จะรัน DAG ครั้งแรกหลังวันนี้
    catchup=False,                  # False = ไม่ย้อนรันวันที่ผ่านมา (backfill)
    tags=DAG_TAGS,                  # ป้ายกำกับสำหรับกรองใน UI
    doc_md=__doc__,                 # __doc__ คือ docstring ด้านบนของไฟล์นี้
                                    # จะแสดงใน Airflow UI ที่หน้า DAG detail
) as dag:

    # PythonOperator คือ "wrapper" ที่บอก Airflow ว่า
    # task นี้ให้รัน Python function อะไร
    # python_callable = function ที่จะถูกเรียก (ส่งแค่ชื่อ ไม่ใส่ ())
    extract = PythonOperator(
        task_id="extract",              # ชื่อ task ใน UI
        python_callable=extract_weather,
    )

    transform = PythonOperator(
        task_id="transform",
        python_callable=transform_weather,
    )

    report = PythonOperator(
        task_id="report",
        python_callable=report_weather,
    )

    # ─── Task Dependencies ──────────────────────────────────────────────
    # ">>" คือ Operator Overloading ใน Python
    # Airflow override operator นี้ให้หมายถึง "ทำก่อน"
    # extract >> transform >> report
    # หมายความว่า: extract ก่อน → แล้ว transform → แล้ว report
    #
    # เทียบ JS: ไม่มี syntax ตรงๆ แต่เหมือนกับ promise chain
    # extract().then(transform).then(report)
    extract >> transform >> report
