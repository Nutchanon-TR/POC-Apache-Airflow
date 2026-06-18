"""
02 — Dynamic Task Mapping (pattern #2)
======================================
Instead of writing one task per greeting, generate them from a list with
``.expand()``. Add/remove items in HELLOS and the number of parallel pods
changes automatically — no DAG-structure edits.

dag_id -> ``02_dynamic_mapping_hello``
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

from common.cluster_aware_kpo import NAMESPACE

HELLOS = ["A", "B", "C", "D"]

with DAG(
    dag_id="02_dynamic_mapping_hello",
    description="Pattern 2: one mapped KPO task expanded over a list of greetings",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["k8s-testing", "kpo", "dynamic-mapping"],
    doc_md=__doc__,
) as dag:
    # .partial() = the args shared by every mapped pod; .expand() = the varying arg.
    KubernetesPodOperator.partial(
        task_id="print_hello",
        name="print-hello",
        namespace=NAMESPACE,
        in_cluster=True,
        image="busybox:1.36",
        cmds=["sh", "-c"],
        on_finish_action="delete_pod",
        get_logs=True,
    ).expand(
        arguments=[[f'echo "Hello {x}"'] for x in HELLOS],
    )
