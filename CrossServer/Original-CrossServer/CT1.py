"""
CT1 DAG
=======

Flow:
    create_mock_file -> upload_to_blob -> [should_trigger_ct2] -> trigger_ct2_dag

Changes vs baseline:
- trigger_ct2_dag now calls Worker/API (ct2-worker-api) instead of CT2 Airflow directly
- upload_to_blob task added after file creation — stores the raw file in Azure Blob (ct1-out/)
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator, ShortCircuitOperator

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


def env_int(name, default):
    raw = env(name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Env var {name} must be an integer") from exc


CT1_OUTPUT_DIR = env("CT1_OUTPUT_DIR", "/opt/airflow/shared/ct1-out")
CT2_DAG_ID = env("CT2_DAG_ID", "ct2_pipeline")
CT2_INPUT_PATH = env("CT2_INPUT_PATH", "/opt/airflow/shared/ct2-in/mock.txt")
WORKER_API_URL = env("WORKER_API_URL", "http://ct2-worker-api:9092")
REQUEST_TIMEOUT_SECONDS = env_int("REQUEST_TIMEOUT_SECONDS", 30)
AZURE_CONN_STR = env("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_CONTAINER = env("AZURE_BLOB_CONTAINER", "crossserver-files")


def create_mock_file(**context):
    params = context["params"]
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


def upload_to_blob(**context):
    file_info = context["ti"].xcom_pull(task_ids="create_mock_file")
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


def should_trigger_ct2(**context):
    return context["params"]["trigger"]


def trigger_ct2_dag(**context):
    # Pull from upload_to_blob (which itself contains file_info)
    file_info = context["ti"].xcom_pull(task_ids="upload_to_blob")

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
    response = requests.post(api_url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    dag_run_id = response.json().get("dagRunId", "")
    logger.info("CT2 triggered via Worker/API — dagRunId: %s", dag_run_id)
    return dag_run_id


with DAG(
    dag_id="ct1_pipeline",
    default_args=DAG_DEFAULT_ARGS,
    description="CT1 creates a mock file, uploads to Azure Blob, then triggers CT2 via Worker/API",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["cross-server", "ct1", "docker-local"],
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
) as dag:
    create_mock_file_task = PythonOperator(
        task_id="create_mock_file",
        python_callable=create_mock_file,
    )

    upload_to_blob_task = PythonOperator(
        task_id="upload_to_blob",
        python_callable=upload_to_blob,
    )

    should_trigger_ct2_task = ShortCircuitOperator(
        task_id="should_trigger_ct2",
        python_callable=should_trigger_ct2,
    )

    trigger_ct2_dag_task = PythonOperator(
        task_id="trigger_ct2_dag",
        python_callable=trigger_ct2_dag,
    )

    create_mock_file_task >> upload_to_blob_task >> should_trigger_ct2_task >> trigger_ct2_dag_task
