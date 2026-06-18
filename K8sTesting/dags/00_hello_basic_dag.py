"""
00 — Hello Basic (the foundation)
=================================
The simplest KubernetesPodOperator chain, run sequentially:

    print HelloA  ->  print HelloB  ->  drop a Hello file into blob storage

Everything else in this folder is a variation on these three jobs.

dag_id = filename prefix -> ``00_hello_basic``
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.models.baseoperator import chain

from common.cluster_aware_kpo import print_pod, upload_hello_pod

with DAG(
    dag_id="00_hello_basic",
    description="Sequential KPO: print HelloA -> HelloB -> upload Hello file to blob",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["k8s-testing", "kpo", "basic"],
    doc_md=__doc__,
) as dag:
    job1 = print_pod("print_hello_a", "HelloA")
    job2 = print_pod("print_hello_b", "HelloB")
    job3 = upload_hello_pod("put_hello_file", blob_name="hello/Hello_basic.txt")

    chain(job1, job2, job3)
