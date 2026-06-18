"""
CT1 DAG – TaskFlow API (Annotation style)
==========================================

Flow:
    create_mock_file
        → upload_to_blob          (Azure Blob: ct1-out/<filename>)
        → should_trigger_ct2      (@task.short_circuit — skips if trigger=False)
        → trigger_ct2_dag         (calls Worker/API → CT2 Airflow)

Changes vs Original:
- PythonOperator / ShortCircuitOperator replaced by @dag / @task / @task.short_circuit
- CT2 trigger goes through Worker/API (ct2-worker-api) instead of CT2 Airflow directly
- Generated file is uploaded to Azure Blob Storage before triggering CT2
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from airflow.decorators import dag, task
from airflow.models.param import Param
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

CT1_OUTPUT_DIR = os.getenv("CT1_OUTPUT_DIR", "/opt/airflow/shared/ct1-out")
CT2_DAG_ID = os.getenv("CT2_DAG_ID", "ct2_pipeline")
CT2_INPUT_PATH = os.getenv("CT2_INPUT_PATH", "/opt/airflow/shared/ct2-in/mock.txt")
WORKER_API_URL = os.getenv("WORKER_API_URL", "http://ct2-worker-api:9092")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
AZURE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "crossserver-files")


@dag(
    dag_id="ct1_pipeline",
    default_args=_DEFAULT_ARGS,
    description="CT1 creates a mock file, uploads to Azure Blob, then triggers CT2 via Worker/API",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["cross-server", "ct1", "annotation"],
    doc_md=__doc__,
    params={
        "context": Param(
            "Hello from CT1 Docker container",
            type="string",
            description="Text content to write into Mock_[datetime].txt",
        ),
        "trigger": Param(
            True,
            type="boolean",
            description="True = trigger ct2_pipeline via Worker/API after creating the file",
        ),
    },
)
def ct1_pipeline():

    @task
    def create_mock_file() -> dict:
        ctx = get_current_context()
        params = ctx["params"]
        mock_context = params["context"]
        should_trigger = params["trigger"]

        now = datetime.now(timezone.utc)
        created_at = now.isoformat()
        filename = f"Mock_{now.strftime('%Y%m%dT%H%M%S%fZ')}.txt"
        output_path = Path(CT1_OUTPUT_DIR) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"{mock_context}\ncreated_at={created_at}\n"
        output_path.write_text(content, encoding="utf-8")
        logger.info("Created mock file: %s", output_path)
        return {
            "source_path": str(output_path),
            "filename": filename,
            "context": mock_context,
            "created_at": created_at,
            "bytes": str(output_path.stat().st_size),
            "trigger_ct2": should_trigger,
        }

    @task
    def upload_to_blob(file_info: dict) -> dict:
        if not AZURE_CONN_STR:
            logger.warning("AZURE_STORAGE_CONNECTION_STRING not set — skipping blob upload")
            return {**file_info, "blob_url": None}

        from azure.storage.blob import BlobServiceClient

        blob_name = f"ct1-out/{file_info['filename']}"
        client = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        container_client = client.get_container_client(AZURE_CONTAINER)

        with open(file_info["source_path"], "rb") as fh:
            container_client.upload_blob(blob_name, fh, overwrite=True)

        blob_url = (
            f"https://{client.account_name}.blob.core.windows.net"
            f"/{AZURE_CONTAINER}/{blob_name}"
        )
        logger.info("Uploaded to Azure Blob: %s", blob_url)
        return {**file_info, "blob_url": blob_url}

    @task.short_circuit
    def should_trigger_ct2(file_info: dict) -> bool:
        return bool(file_info.get("trigger_ct2", False))

    @task
    def trigger_ct2_dag(file_info: dict) -> str:
        api_url = f"{WORKER_API_URL.rstrip('/')}/api/airflow/trigger"
        payload = {
            "dagId": CT2_DAG_ID,
            "conf": {
                "source_path": file_info["source_path"],
                "target_path": CT2_INPUT_PATH,
                "filename": file_info["filename"],
                "source_created_at": file_info["created_at"],
                "source_bytes": file_info["bytes"],
            },
        }
        response = requests.post(api_url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        dag_run_id = response.json().get("dagRunId", "")
        logger.info("CT2 triggered via Worker/API — dagRunId: %s", dag_run_id)
        return dag_run_id

    # ── dependency wiring ────────────────────────────────────────────────────
    file_info = create_mock_file()
    uploaded = upload_to_blob(file_info)
    gate = should_trigger_ct2(uploaded)
    trigger_result = trigger_ct2_dag(uploaded)
    gate >> trigger_result  # short_circuit controls whether trigger runs


ct1_pipeline()
