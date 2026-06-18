"""
06 — WasbBlobSensor (pattern #6): wait for a file in blob storage
=================================================================
This DAG demonstrates the "a file lands in storage, then we react" case using
``WasbBlobSensor``. The sensor POLLS the blob container until the blob exists,
then a pod prints that it arrived.

    wait_for_hello_blob (poll)  ─►  print "file arrived"

Important (from the doc): a Sensor is PULL, not PUSH. The DAG must already be
running (triggered manually, on schedule, or by DAG 05) for the sensor to start
polling. It does NOT get pushed by the blob itself. For true push (blob-created
-> DAG fires) you'd wire Azure Event Grid to the Airflow REST API.

``mode="reschedule"`` frees the worker slot between pokes.

dag_id -> ``06_wasb_sensor_hello``
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.microsoft.azure.sensors.wasb import WasbBlobSensor

from common.cluster_aware_kpo import BLOB_CONTAINER, print_pod

BLOB_NAME = "hello/Hello.txt"

with DAG(
    dag_id="06_wasb_sensor_hello",
    description="Pattern 6: WasbBlobSensor waits for a blob, then reacts",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["k8s-testing", "sensor", "wasb"],
    doc_md=__doc__,
) as dag:
    wait_for_hello_blob = WasbBlobSensor(
        task_id="wait_for_hello_blob",
        wasb_conn_id="wasb_default",
        container_name=BLOB_CONTAINER,
        blob_name=BLOB_NAME,
        poke_interval=30,   # check every 30s
        timeout=600,        # give up after 10 min
        mode="reschedule",  # don't hold a worker slot while waiting
    )

    react = print_pod("file_arrived", f"Found {BLOB_CONTAINER}/{BLOB_NAME} — reacting now")

    wait_for_hello_blob >> react
