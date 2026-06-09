"""
CT1 DAG
=======

Flow:
    create_mock_file -> [should_trigger_ct2] -> trigger_ct2_dag

This DAG uses the classic Airflow DAG + PythonOperator style. It creates a
mock file on CT1, then optionally calls the Airflow REST API on CT2. The local
Docker compose stack provides the CT2 API URL and credentials as environment
variables.
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
    raw_value = env(name, str(default))
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer") from exc


CT1_OUTPUT_DIR = env("CT1_OUTPUT_DIR", "/tmp/crossserver/out")
CT2_DAG_ID = env("CT2_DAG_ID", "ct2_pipeline")
CT2_INPUT_PATH = env("CT2_INPUT_PATH", "/tmp/crossserver/in/mock.txt")
CT2_AIRFLOW_URL = env("CT2_AIRFLOW_URL", "http://ct2-webserver:8080")
CT2_AIRFLOW_USER = env("CT2_AIRFLOW_USER", "airflow")
CT2_AIRFLOW_PASSWORD = env("CT2_AIRFLOW_PASSWORD", "airflow")
REQUEST_TIMEOUT_SECONDS = env_int("REQUEST_TIMEOUT_SECONDS", 30)


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


def should_trigger_ct2(**context):
    return context["params"]["trigger"]


def trigger_ct2_dag(**context):
    file_info = context["ti"].xcom_pull(task_ids="create_mock_file")

    api_url = f"{CT2_AIRFLOW_URL.rstrip('/')}/api/v1/dags/{CT2_DAG_ID}/dagRuns"
    payload = {
        "conf": {
            "source_path": file_info["source_path"],
            "target_path": CT2_INPUT_PATH,
            "filename": file_info["filename"],
            "source_created_at": file_info["created_at"],
            "source_bytes": file_info["bytes"],
        }
    }

    response = requests.post(
        api_url,
        json=payload,
        auth=(CT2_AIRFLOW_USER, CT2_AIRFLOW_PASSWORD),
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    dag_run_id = response.json().get("dag_run_id", "")
    logger.info("Triggered CT2 DAG run: %s", dag_run_id)
    return dag_run_id


with DAG(
    dag_id="ct1_pipeline",
    default_args=DAG_DEFAULT_ARGS,
    description="CT1 creates a mock file and optionally triggers CT2",
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
            description="True = trigger ct2_pipeline after creating the file",
        ),
    },
) as dag:
    create_mock_file_task = PythonOperator(
        task_id="create_mock_file",
        python_callable=create_mock_file,
    )

    should_trigger_ct2_task = ShortCircuitOperator(
        task_id="should_trigger_ct2",
        python_callable=should_trigger_ct2,
    )

    trigger_ct2_dag_task = PythonOperator(
        task_id="trigger_ct2_dag",
        python_callable=trigger_ct2_dag,
    )

    create_mock_file_task >> should_trigger_ct2_task >> trigger_ct2_dag_task
