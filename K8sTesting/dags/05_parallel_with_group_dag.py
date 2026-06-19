"""
05 — Parallel tasks running ALONGSIDE a TaskGroup
=================================================
Mixes two ideas: plain parallel tasks AND a TaskGroup, all fanning out in
parallel from ``start`` and converging at ``finalize``.

    start ─┬─► solo_1 ───────────────┐
           ├─► solo_2 ───────────────┤
           └─► [ batch ]             ├─► finalize
               ├─ grp_a ─┐          │
               │         ├─► (group)┘
               └─ grp_b ─┘

Point of comparison vs DAG 01:
- ``solo_1`` / ``solo_2`` are TOP-LEVEL tasks — parallel but NOT grouped.
- ``batch`` is a TaskGroup — its members are parallel AND boxed together in the
  UI, and you wire the whole group as one node.
- A TaskGroup is purely a VISUAL/organisational grouping; it does NOT change
  execution. ``solo_1``, ``solo_2`` and everything in ``batch`` all run at the
  same time (LocalExecutor). Grouping just tidies the graph and lets you depend
  on the group as a unit.

dag_id -> ``05_parallel_with_group``
"""

from __future__ import annotations

import logging
from datetime import datetime

from airflow.decorators import dag, task, task_group
from airflow.utils.trigger_rule import TriggerRule

log = logging.getLogger(__name__)


@dag(
    dag_id="05_parallel_with_group",
    description="Top-level parallel tasks running alongside a TaskGroup",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["aci", "taskflow", "parallel", "taskgroup"],
    doc_md=__doc__,
)
def parallel_with_group():

    @task
    def start() -> None:
        log.info("start — fan out")

    # plain parallel tasks (not in any group)
    @task
    def solo_1() -> None:
        log.info("solo_1 (top-level parallel)")

    @task
    def solo_2() -> None:
        log.info("solo_2 (top-level parallel)")

    # a group whose members are also parallel
    @task_group(group_id="batch")
    def batch():
        @task
        def grp_a() -> None:
            log.info("grp_a (inside group)")

        @task
        def grp_b() -> None:
            log.info("grp_b (inside group)")

        grp_a()
        grp_b()

    @task(trigger_rule=TriggerRule.ALL_DONE)
    def finalize() -> None:
        log.info("finalize — all parallel work (solo + group) is done")

    begin = start()
    end = finalize()

    # solo tasks AND the whole group all run in parallel between start and finalize
    begin >> [solo_1(), solo_2(), batch()] >> end


parallel_with_group()
