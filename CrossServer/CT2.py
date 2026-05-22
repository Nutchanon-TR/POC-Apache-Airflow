"""
CT2 DAG
=======

Flow:
    sftp_fetch_file -> reverse_text

This DAG is triggered by CT1. It receives the CT1 file path through dag_run.conf,
reads CT1 SSH/SFTP credentials from Azure Key Vault, downloads the file, then
writes a reversed-text output file.
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import paramiko
from airflow import DAG
from airflow.operators.python import PythonOperator
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

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


CT1_DEFAULT_SOURCE_PATH = env(
    "CT1_DEFAULT_SOURCE_PATH",
    "/tmp/crossserver/out/Mock_latest.txt",
)
CT1_SFTP_PORT = env_int("CT1_SFTP_PORT", 22)
CT2_INPUT_PATH = env("CT2_INPUT_PATH", "/tmp/crossserver/in/mock.txt")
CT2_REVERSED_OUTPUT_PATH = env(
    "CT2_REVERSED_OUTPUT_PATH",
    "/tmp/crossserver/out/mock_reversed.txt",
)
VAULT_URL = env("VAULT_URL", "https://kv-airflow-demo.vault.azure.net/")
SSH_TIMEOUT_SECONDS = env_int("SSH_TIMEOUT_SECONDS", 30)


def dag_conf(context):
    dag_run = context.get("dag_run")
    return dag_run.conf if dag_run and dag_run.conf else {}


def connect_to_ct1():
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=VAULT_URL, credential=credential)

    host = client.get_secret("CT1-HOST").value
    user = client.get_secret("CT1-USER").value
    password = client.get_secret("CT1-PASSWORD").value

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        "hostname": host,
        "port": CT1_SFTP_PORT,
        "username": user,
        "password": password,
        "timeout": SSH_TIMEOUT_SECONDS,
        "look_for_keys": False,
        "allow_agent": False,
    }

    ssh.connect(**connect_kwargs)
    return ssh


def sftp_fetch_file(**context):
    conf = dag_conf(context)
    source_path = conf.get("source_path", CT1_DEFAULT_SOURCE_PATH)
    target_path = Path(conf.get("target_path", CT2_INPUT_PATH))
    target_path.parent.mkdir(parents=True, exist_ok=True)

    ssh = connect_to_ct1()
    try:
        sftp = ssh.open_sftp()
        try:
            sftp.get(source_path, str(target_path))
        finally:
            sftp.close()
    finally:
        ssh.close()

    logger.info("Fetched %s from CT1 VM -> %s", source_path, target_path)
    return {
        "source_path": source_path,
        "input_path": str(target_path),
        "bytes": str(target_path.stat().st_size),
    }


def reverse_text(**context):
    file_info = context["ti"].xcom_pull(task_ids="sftp_fetch_file")
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
    description="CT2 fetches CT1 file over SFTP and reverses text",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["cross-server", "ct2", "azure-key-vault"],
    doc_md=__doc__,
) as dag:
    sftp_fetch_file_task = PythonOperator(
        task_id="sftp_fetch_file",
        python_callable=sftp_fetch_file,
    )

    reverse_text_task = PythonOperator(
        task_id="reverse_text",
        python_callable=reverse_text,
    )

    sftp_fetch_file_task >> reverse_text_task
