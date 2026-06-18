"""
05 — Trigger another DAG (pattern #5)
=====================================
Upstream DAG: print -> upload a Hello file to blob -> then trigger the
downstream sensor DAG (``06_wasb_sensor_hello``) with TriggerDagRunOperator.

This is the "push / direct call" style: this DAG knows the name of the DAG it
triggers and can pass ``conf`` to it.

    print_hello ─► upload (hello/Hello.txt) ─► trigger 06_wasb_sensor_hello

dag_id -> ``05_trigger_downstream``
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.models.baseoperator import chain
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from common.cluster_aware_kpo import print_pod, upload_hello_pod

DOWNSTREAM_DAG_ID = "06_wasb_sensor_hello"

with DAG(
    dag_id="05_trigger_downstream",
    description="Pattern 5: upload Hello file, then TriggerDagRunOperator -> 06",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["k8s-testing", "kpo", "trigger-dagrun"],
    doc_md=__doc__,
) as dag:
    hello = print_pod("print_hello", "HelloA")
    # Upload to the exact blob 06's sensor is waiting for.
    upload = upload_hello_pod("put_hello_file", blob_name="hello/Hello.txt")

    trigger = TriggerDagRunOperator(
        task_id="trigger_sensor_dag",
        trigger_dag_id=DOWNSTREAM_DAG_ID,
        conf={"triggered_by": "05_trigger_downstream"},
    )

    chain(hello, upload, trigger)
