"""
Shared KubernetesPodOperator helpers for the K8sTesting demos
=============================================================

Two things live here:

1. ``ClusterAwareKubernetesPodOperator`` — the doc's pattern: a KPO subclass
   that picks its target cluster at runtime in ``pre_execute()``. In this
   single-cluster POC it falls back to ``in_cluster=True``, but the hook shows
   exactly where multi-cluster routing would plug in.

2. ``print_pod`` / ``upload_hello_pod`` — tiny factories so each demo DAG stays
   short and readable instead of repeating KPO boilerplate.

All pods run on the SAME AKS cluster Airflow runs in (``in_cluster=True``). The
scheduler ServiceAccount (``airflow-kpo``) is granted pod-launch RBAC by
Terraform, so KPO can create these pods.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret

logger = logging.getLogger(__name__)

NAMESPACE = os.getenv("AIRFLOW_KPO_NAMESPACE", "airflow")
BLOB_CONTAINER = os.getenv("HELLO_BLOB_CONTAINER", "hello-demo")

# Storage connection string, injected into the upload pod as an env var.
# Comes from the k8s Secret `azure-storage` that Terraform creates.
_AZURE_SECRET = Secret(
    deploy_type="env",
    deploy_target="AZURE_STORAGE_CONNECTION_STRING",
    secret="azure-storage",
    key="AZURE_STORAGE_CONNECTION_STRING",
)

# Config file the doc's ClusterAware pattern would read to map project -> cluster.
_CLUSTER_CONFIG_PATH = os.getenv("CLUSTER_CONNECTION_CONFIG", "")


def _safe_name(task_id: str) -> str:
    """Pod names must be DNS-1123: lowercase, hyphens, no underscores."""
    return task_id.replace("_", "-").lower()


class ClusterAwareKubernetesPodOperator(KubernetesPodOperator):
    """KPO that resolves its cluster at runtime (see 03-airflow-patterns.md)."""

    def __init__(self, project: str = "default", **kwargs):
        kwargs.setdefault("in_cluster", True)
        kwargs.setdefault("namespace", NAMESPACE)
        super().__init__(**kwargs)
        self._project = project

    def pre_execute(self, context):
        cluster = "in-cluster"
        if _CLUSTER_CONFIG_PATH and Path(_CLUSTER_CONFIG_PATH).exists():
            cfg = json.loads(Path(_CLUSTER_CONFIG_PATH).read_text())
            cluster = cfg.get(self._project, "in-cluster")
            # Real multi-cluster routing would do:
            #   self.kubernetes_conn_id = cluster
            #   self.cluster_context = cluster
            #   self.in_cluster = False
        logger.info("project=%s -> cluster=%s", self._project, cluster)
        super().pre_execute(context)


def print_pod(task_id: str, message: str, **kwargs) -> KubernetesPodOperator:
    """A pod that just prints a message (busybox echo)."""
    return KubernetesPodOperator(
        task_id=task_id,
        name=_safe_name(f"print-{task_id}"),
        namespace=NAMESPACE,
        in_cluster=True,
        image="busybox:1.36",
        cmds=["sh", "-c"],
        arguments=[f'echo "{message}"'],
        on_finish_action="delete_pod",
        get_logs=True,
        **kwargs,
    )


def upload_hello_pod(
    task_id: str,
    blob_name: str = "hello/Hello.txt",
    content: str = "Hello from Airflow KubernetesPodOperator",
    **kwargs,
) -> KubernetesPodOperator:
    """A pod that writes a file and uploads it to the blob container via az-cli."""
    script = (
        f'echo "{content}" > /tmp/hello.txt && '
        f'az storage blob upload '
        f'--connection-string "$AZURE_STORAGE_CONNECTION_STRING" '
        f'--container-name "{BLOB_CONTAINER}" '
        f'--name "{blob_name}" '
        f'--file /tmp/hello.txt --overwrite --only-show-errors && '
        f'echo "uploaded {BLOB_CONTAINER}/{blob_name}"'
    )
    return KubernetesPodOperator(
        task_id=task_id,
        name=_safe_name(f"upload-{task_id}"),
        namespace=NAMESPACE,
        in_cluster=True,
        image="mcr.microsoft.com/azure-cli:latest",
        cmds=["sh", "-c"],
        arguments=[script],
        secrets=[_AZURE_SECRET],
        on_finish_action="delete_pod",
        get_logs=True,
        **kwargs,
    )
