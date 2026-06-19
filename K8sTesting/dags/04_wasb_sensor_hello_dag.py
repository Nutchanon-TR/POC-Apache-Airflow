"""
04 — WasbBlobSensor: wait for a file in Blob storage
====================================================
Demonstrates the "a file lands in storage, then we react" case using
``WasbBlobSensor``. The sensor POLLS the blob container until the blob exists,
then a task reacts.

    wait_for_hello_blob (poll)  ─►  react

Important: a Sensor is PULL, not PUSH. The DAG must already be running (manual,
schedule, or triggered by DAG 03) for the sensor to start polling — the blob
does not push to it. For true push (blob-created -> DAG fires) you'd wire Azure
Event Grid to the Airflow REST API.

``mode="reschedule"`` frees the worker slot between pokes.

dag_id -> ``04_wasb_sensor_hello``
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from airflow.decorators import dag, task
from airflow.providers.microsoft.azure.sensors.wasb import WasbBlobSensor

log = logging.getLogger(__name__)

BLOB_CONTAINER = os.getenv("HELLO_BLOB_CONTAINER", "hello-demo")
BLOB_NAME = "hello/Hello.txt"


@dag(
    dag_id="04_wasb_sensor_hello",
    description="WasbBlobSensor waits for a blob, then reacts",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["aci", "sensor", "wasb"],
    doc_md=__doc__,
)
def wasb_sensor_hello():

    wait_for_hello_blob = WasbBlobSensor(
        task_id="wait_for_hello_blob",
        wasb_conn_id="wasb_default",
        container_name=BLOB_CONTAINER,
        blob_name=BLOB_NAME,
        poke_interval=30,   # check every 30s
        timeout=600,        # give up after 10 min
        mode="reschedule",  # don't hold a worker slot while waiting
    )

    @task
    def react() -> None:
        log.info("Found %s/%s — reacting now", BLOB_CONTAINER, BLOB_NAME)

    wait_for_hello_blob >> react()


wasb_sensor_hello()
