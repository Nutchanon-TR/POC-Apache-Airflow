"""
03 — TaskGroup (pattern #3)
===========================
Group the two print jobs into a TaskGroup so the UI stays tidy. Inside the
group they run in parallel; the group as a whole feeds the upload.

    ┌ greet ───────────────┐
    │ HelloA ─┐            │
    │         ├─► (group) ─┼─► upload
    │ HelloB ─┘            │
    └──────────────────────┘

dag_id -> ``03_taskgroup_hello``
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.utils.task_group import TaskGroup

from common.cluster_aware_kpo import print_pod, upload_hello_pod

with DAG(
    dag_id="03_taskgroup_hello",
    description="Pattern 3: TaskGroup grouping parallel print jobs, then upload",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["k8s-testing", "kpo", "taskgroup"],
    doc_md=__doc__,
) as dag:
    with TaskGroup("greet") as greet:
        print_pod("print_hello_a", "HelloA")
        print_pod("print_hello_b", "HelloB")

    upload = upload_hello_pod("put_hello_file", blob_name="hello/Hello_taskgroup.txt")

    greet >> upload
