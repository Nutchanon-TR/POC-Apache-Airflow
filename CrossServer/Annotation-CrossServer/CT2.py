"""
CT2 DAG – TaskFlow API (Annotation style)
==========================================

Flow:
    copy_mock_file      (reads dag_run.conf from CT1 trigger)
        → call_batch_reverse  (delegates reversal to Worker/Batch via HTTP)

Changes vs Original:
- PythonOperator replaced by @dag / @task
- Text reversal is no longer done in Airflow — Worker/Batch handles it
- Worker/Batch also uploads the reversed file to Azure Blob Storage
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import requests
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

logger = logging.getLogger(__name__)

_DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

CT1_DEFAULT_SOURCE_PATH = os.getenv(
    "CT1_DEFAULT_SOURCE_PATH", "/opt/airflow/shared/ct1-out/Mock_latest.txt"
)
CT2_INPUT_PATH = os.getenv("CT2_INPUT_PATH", "/opt/airflow/shared/ct2-in/mock.txt")
CT2_REVERSED_OUTPUT_PATH = os.getenv(
    "CT2_REVERSED_OUTPUT_PATH", "/opt/airflow/shared/ct2-out/mock_reversed.txt"
)
WORKER_BATCH_URL = os.getenv("WORKER_BATCH_URL", "http://worker-batch:9091")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))


@dag(
    dag_id="ct2_pipeline",
    default_args=_DEFAULT_ARGS,
    description="CT2 copies a CT1 file from shared volume, then delegates reversal to Worker/Batch",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["cross-server", "ct2", "annotation"],
    doc_md=__doc__,
)
def ct2_pipeline():

    @task
    def copy_mock_file() -> dict:
        ctx = get_current_context()
        dag_run = ctx.get("dag_run")
        conf = dag_run.conf if dag_run and dag_run.conf else {}

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

    @task
    def call_batch_reverse(file_info: dict) -> dict:
        api_url = f"{WORKER_BATCH_URL.rstrip('/')}/batch/reverse"
        payload = {
            "inputPath": file_info["input_path"],
            "outputPath": CT2_REVERSED_OUTPUT_PATH,
        }
        response = requests.post(api_url, json=payload, timeout=REQUEST_TIMEOUT)
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

    # ── dependency wiring ────────────────────────────────────────────────────
    file_info = copy_mock_file()
    call_batch_reverse(file_info)


ct2_pipeline()
