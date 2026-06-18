"""
04 — Branching (pattern #4)
===========================
A ``@task.branch`` decides at runtime whether to upload the Hello file or skip
it, based on the ``do_upload`` param. The two paths re-join at ``done`` using
``trigger_rule="none_failed_min_one_success"`` so it runs no matter which branch
was taken (the doc's gotcha).

    print_hello ─► choose ─┬─► upload ──┐
                          └─► skip ─────┴─► done

dag_id -> ``04_branch_hello``
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.decorators import task
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import get_current_context
from airflow.models.param import Param
from airflow.utils.trigger_rule import TriggerRule

from common.cluster_aware_kpo import print_pod, upload_hello_pod

with DAG(
    dag_id="04_branch_hello",
    description="Pattern 4: @task.branch chooses upload vs skip, then re-joins",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["k8s-testing", "kpo", "branch"],
    doc_md=__doc__,
    params={
        "do_upload": Param(True, type="boolean", description="True = upload, False = skip"),
    },
) as dag:
    hello = print_pod("print_hello", "HelloA")

    @task.branch
    def choose() -> str:
        do_upload = get_current_context()["params"]["do_upload"]
        return "put_hello_file" if do_upload else "skip_upload"

    upload = upload_hello_pod("put_hello_file", blob_name="hello/Hello_branch.txt")
    skip = EmptyOperator(task_id="skip_upload")
    done = EmptyOperator(task_id="done", trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)

    branch = choose()
    hello >> branch >> [upload, skip] >> done
