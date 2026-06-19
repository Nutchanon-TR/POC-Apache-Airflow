"""
03 — Trigger another DAG
========================
Upstream DAG: say hello -> upload a Hello file to Blob -> then trigger the
downstream sensor DAG (``04_wasb_sensor_hello``) with TriggerDagRunOperator.

"Push / direct call" style: this DAG knows the name of the DAG it triggers and
passes ``conf`` to it.

    hello ─► upload (hello/Hello.txt) ─► trigger 04_wasb_sensor_hello

dag_id -> ``03_trigger_downstream``
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from airflow.decorators import dag, task
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

log = logging.getLogger(__name__)

BLOB_CONTAINER = os.getenv("HELLO_BLOB_CONTAINER", "hello-demo")
DOWNSTREAM_DAG_ID = "04_wasb_sensor_hello"


def _upload_blob(blob_name: str, content: str) -> str:
    from azure.storage.blob import BlobServiceClient

    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    client = BlobServiceClient.from_connection_string(conn).get_container_client(BLOB_CONTAINER)
    client.upload_blob(blob_name, content, overwrite=True)
    log.info("uploaded %s/%s", BLOB_CONTAINER, blob_name)
    return blob_name


@dag(
    dag_id="03_trigger_downstream",
    description="Upload Hello.txt, then TriggerDagRunOperator -> 04",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["aci", "taskflow", "trigger-dagrun"],
    doc_md=__doc__,
)
def trigger_downstream():

    @task
    def hello() -> None:
        log.info("HelloA")

    @task
    def upload() -> str:
        # Upload the exact blob 04's sensor waits for.
        return _upload_blob("hello/Hello.txt", "Hello from the trigger demo")

    trigger = TriggerDagRunOperator(
        task_id="trigger_sensor_dag",
        trigger_dag_id=DOWNSTREAM_DAG_ID,
        conf={"triggered_by": "03_trigger_downstream"},
    )

    hello() >> upload() >> trigger


trigger_downstream()
