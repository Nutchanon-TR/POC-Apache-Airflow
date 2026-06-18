"""
01 — Parallel (pattern #1)
==========================
HelloA and HelloB have no dependency on each other, so they run in parallel,
then both feed the upload job.

    print HelloA ─┐
                  ├─► upload Hello file
    print HelloB ─┘

Key idea from the doc: parallelism is just "don't wire a dependency between them".

dag_id -> ``01_parallel_hello``
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG

from common.cluster_aware_kpo import print_pod, upload_hello_pod

with DAG(
    dag_id="01_parallel_hello",
    description="Pattern 1: HelloA || HelloB run in parallel, then upload",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["k8s-testing", "kpo", "parallel"],
    doc_md=__doc__,
) as dag:
    job_a = print_pod("print_hello_a", "HelloA")
    job_b = print_pod("print_hello_b", "HelloB")
    upload = upload_hello_pod("put_hello_file", blob_name="hello/Hello_parallel.txt")

    [job_a, job_b] >> upload
