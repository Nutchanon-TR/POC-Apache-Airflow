"""
weather_dag.py
==============
Airflow DAG — Weather Pipeline (POC)

Orchestration layer only. Business logic lives in dedicated modules:
  • config/settings.py  — all constants and tunables
  • tasks/extract.py    — fetch from Open-Meteo API
  • tasks/transform.py  — compute derived metrics (pure Python)
  • tasks/report.py     — log results to Airflow UI

Pipeline:
    extract → transform → report

Schedule: Daily at 06:00 UTC
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from config.settings import DAG_DEFAULT_ARGS, DAG_ID, DAG_SCHEDULE, DAG_TAGS
from tasks.extract import extract_weather
from tasks.transform import transform_weather
from tasks.report import report_weather

# ─── DAG ───────────────────────────────────────────────────────────────
with DAG(
    dag_id=DAG_ID,
    default_args=DAG_DEFAULT_ARGS,
    description="Weather pipeline: Open-Meteo API → Transform → Report",
    schedule=DAG_SCHEDULE,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=DAG_TAGS,
    doc_md=__doc__,
) as dag:

    extract = PythonOperator(
        task_id="extract",
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

    # ── Task Dependencies ───────────────────────────────────────────────
    extract >> transform >> report
