"""
CT2 DAG
=======

Flow:
    copy_mock_file -> call_batch_reverse

Changes vs baseline:
- reverse_text task replaced by call_batch_reverse — delegates to Worker/Batch via HTTP
- Worker/Batch performs the text reversal and uploads the reversed file to Azure Blob
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import requests
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
    "/opt/airflow/shared/ct1-out/Mock_latest.txt",
)
CT2_INPUT_PATH = env("CT2_INPUT_PATH", "/opt/airflow/shared/ct2-in/mock.txt")
CT2_REVERSED_OUTPUT_PATH = env(
    "CT2_REVERSED_OUTPUT_PATH",
    "/opt/airflow/shared/ct2-out/mock_reversed.txt",
)
WORKER_BATCH_URL = env("WORKER_BATCH_URL", "http://worker-batch:9091")
REQUEST_TIMEOUT_SECONDS = int(env("REQUEST_TIMEOUT_SECONDS", "30"))


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
        raise FileNotFoundError(
            f"CT1 mock file is not available in shared volume: {source}"
        )

    shutil.copy2(source, target_path)
    logger.info("Copied %s → %s", source, target_path)
    return {
        "source_path": str(source),
        "input_path": str(target_path),
        "bytes": str(target_path.stat().st_size),
    }


def call_batch_reverse(**context):
    file_info = context["ti"].xcom_pull(task_ids="copy_mock_file")
    api_url = f"{WORKER_BATCH_URL.rstrip('/')}/batch/reverse"
    payload = {
        "inputPath": file_info["input_path"],
        "outputPath": CT2_REVERSED_OUTPUT_PATH,
    }
    response = requests.post(api_url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    result = response.json()
    logger.info(
        "Worker/Batch reversed file: %s → %s (blobUrl=%s)",
        file_info["input_path"],
        CT2_REVERSED_OUTPUT_PATH,
        result.get("blobUrl"),
    )
    return {
        "input_path": file_info["input_path"],
        "output_path": CT2_REVERSED_OUTPUT_PATH,
        "bytes": str(result.get("bytes", 0)),
        "blob_url": result.get("blobUrl"),
    }


with DAG(
    dag_id="ct2_pipeline",
    default_args=DAG_DEFAULT_ARGS,
    description="CT2 copies a CT1 file from shared volume and delegates reversal to Worker/Batch",
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

    call_batch_reverse_task = PythonOperator(
        task_id="call_batch_reverse",
        python_callable=call_batch_reverse,
    )

    copy_mock_file_task >> call_batch_reverse_task
