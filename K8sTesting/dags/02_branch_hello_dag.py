"""
02 — Branching into two different multi-step chains
===================================================
A ``@task.branch`` chooses ONE of two whole chains at runtime, then both chains
rejoin at ``c``:

    choose ─┬─ (go_left=True)  ─► a ─► b ─┐
            │                             ├─► c   (merge)
            └─ (go_left=False) ─► x ─► y ─┘

- Pick the path with the ``go_left`` param when you trigger the DAG.
- The not-chosen chain is skipped (greyed out in the UI), skip flows down it.
- ``c`` uses ``trigger_rule="none_failed_min_one_success"`` so it still runs
  even though one of its upstream chains was skipped.

dag_id -> ``02_branch_hello``
"""

from __future__ import annotations

import logging
from datetime import datetime

from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.python import get_current_context
from airflow.utils.trigger_rule import TriggerRule

log = logging.getLogger(__name__)


@dag(
    dag_id="02_branch_hello",
    description="@task.branch picks chain A->B or X->Y, both merge at C",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["aci", "taskflow", "branch"],
    doc_md=__doc__,
    params={
        "go_left": Param(True, type="boolean", description="True = A->B->C, False = X->Y->C"),
    },
)
def branch_hello():

    @task.branch
    def choose() -> str:
        go_left = get_current_context()["params"]["go_left"]
        return "a" if go_left else "x"

    # ── left chain ───────────────────────────────────────────────────────────
    @task
    def a() -> None:
        log.info("A — left chain start")

    @task
    def b() -> None:
        log.info("B — left chain")

    # ── right chain ──────────────────────────────────────────────────────────
    @task
    def x() -> None:
        log.info("X — right chain start")

    @task
    def y() -> None:
        log.info("Y — right chain")

    # ── merge point ──────────────────────────────────────────────────────────
    @task(trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
    def c() -> None:
        log.info("C — merged; runs whichever chain was taken")

    branch = choose()
    left_b = b()
    right_y = y()
    merge = c()

    branch >> a() >> left_b >> merge
    branch >> x() >> right_y >> merge


branch_hello()
