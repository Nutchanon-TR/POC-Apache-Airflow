"""
CT2 DAG
=======

Flow:
    copy_mock_file -> reverse_text

This DAG is triggered by CT1. It receives the CT1 file path through dag_run.conf,
copies the file from the shared Docker volume, then writes a reversed-text
output file.
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

DAG_DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def env(name, default=""):
    return os.getenv(name, default).strip()


CT1_DEFAULT_SOURCE_PATH = env(
    "CT1_DEFAULT_SOURCE_PATH",
    "/tmp/crossserver/out/Mock_latest.txt",
)
CT2_INPUT_PATH = env("CT2_INPUT_PATH", "/tmp/crossserver/in/mock.txt")
CT2_REVERSED_OUTPUT_PATH = env(
    "CT2_REVERSED_OUTPUT_PATH",
    "/tmp/crossserver/out/mock_reversed.txt",
)


def dag_conf(context):
    dag_run = context.get("dag_run")
    return dag_run.conf if dag_run and dag_run.conf else {}


def copy_mock_file(**context):
    conf = dag_conf(context)
    source_path = conf.get("source_path", CT1_DEFAULT_SOURCE_PATH)
    target_path = Path(conf.get("target_path", CT2_INPUT_PATH))
    target_path.parent.mkdir(parents=True, exist_ok=True)

    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"CT1 mock file is not available in shared volume: {source}")

    shutil.copy2(source, target_path)
    logger.info("Copied %s from shared CT1 volume -> %s", source, target_path)
    return {
        "source_path": str(source),
        "input_path": str(target_path),
        "bytes": str(target_path.stat().st_size),
    }


def reverse_text(**context):
    file_info = context["ti"].xcom_pull(task_ids="copy_mock_file")
    input_path = Path(file_info["input_path"])
    output_path = Path(CT2_REVERSED_OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = input_path.read_text(encoding="utf-8")
    output_path.write_text(content[::-1], encoding="utf-8")

    logger.info("Wrote reversed text to: %s", output_path)
    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "bytes": str(output_path.stat().st_size),
    }


with DAG(
    dag_id="ct2_pipeline",
    default_args=DAG_DEFAULT_ARGS,
    description="CT2 copies a CT1 file from a Docker shared volume and reverses text",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["cross-server", "ct2", "docker-local"],
    doc_md=__doc__,
) as dag:
    copy_mock_file_task = PythonOperator(
        task_id="copy_mock_file",
        python_callable=copy_mock_file,
    )

    reverse_text_task = PythonOperator(
        task_id="reverse_text",
        python_callable=reverse_text,
    )

    copy_mock_file_task >> reverse_text_task
