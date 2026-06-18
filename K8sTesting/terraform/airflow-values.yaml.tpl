# Lightweight Airflow: LocalExecutor + git-sync. Heavy/optional components off.
executor: LocalExecutor

# Bundled Postgres (LocalExecutor needs a real DB to run tasks in parallel).
postgresql:
  enabled: true

# Not needed for LocalExecutor / this POC -> disabled to save the single node.
redis:
  enabled: false
flower:
  enabled: false
statsd:
  enabled: false
triggerer:
  enabled: false

# No public IP. Reach the UI with `kubectl port-forward` (see outputs).
webserver:
  service:
    type: ClusterIP

# Scheduler runs LocalExecutor tasks in-process, so its ServiceAccount is what
# KubernetesPodOperator uses (in_cluster=True). Point it at our RBAC'd SA.
scheduler:
  serviceAccount:
    create: false
    name: ${kpo_sa}

# Applied to every Airflow container.
env:
  - name: _PIP_ADDITIONAL_REQUIREMENTS
    value: "apache-airflow-providers-microsoft-azure"
  - name: AIRFLOW_CONN_WASB_DEFAULT
    valueFrom:
      secretKeyRef:
        name: ${secret_name}
        key: AIRFLOW_CONN_WASB_DEFAULT

# Pull DAGs from the public repo (no auth needed).
dags:
  gitSync:
    enabled: true
    repo: ${git_repo}
    branch: ${git_branch}
    subPath: ${git_subpath}
    wait: 60
