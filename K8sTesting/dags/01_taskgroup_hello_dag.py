"""
01 — TaskGroup
==============
Group two parallel "hello" tasks under one TaskGroup so the UI stays tidy, then
upload a file to Blob storage. Inside the group the tasks run in parallel; the
group as a whole feeds the upload.

    ┌ greet ──────────┐
    │ hello_a ─┐      │
    │          ├─► () ┼─► upload
    │ hello_b ─┘      │
    └─────────────────┘

Pure TaskFlow (@dag / @task / @task_group). Tasks run inside Airflow itself
(on the Azure Container Instance) — no Kubernetes.

dag_id -> ``01_taskgroup_hello``
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from airflow.decorators import dag, task, task_group

log = logging.getLogger(__name__)

BLOB_CONTAINER = os.getenv("HELLO_BLOB_CONTAINER", "hello-demo")


def _upload_blob(blob_name: str, content: str) -> str:
    """Upload text to the demo container; returns the blob name."""
    from azure.storage.blob import BlobServiceClient

    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    client = BlobServiceClient.from_connection_string(conn).get_container_client(BLOB_CONTAINER)
    client.upload_blob(blob_name, content, overwrite=True)
    log.info("uploaded %s/%s", BLOB_CONTAINER, blob_name)
    return blob_name


@dag(
    dag_id="01_taskgroup_hello",
    description="TaskGroup grouping parallel hello tasks, then upload",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["aci", "taskflow", "taskgroup"],
    doc_md=__doc__,
)
def taskgroup_hello():

    @task_group(group_id="greet")
    def greet():
        @task
        def hello_a() -> str:
            log.info("HelloA")
            return "HelloA"

        @task
        def hello_b() -> str:
            log.info("HelloB")
            return "HelloB"

        hello_a()
        hello_b()

    @task
    def upload() -> str:
        return _upload_blob("hello/Hello_taskgroup.txt", "Hello from the TaskGroup demo")

    greet() >> upload()


taskgroup_hello()
