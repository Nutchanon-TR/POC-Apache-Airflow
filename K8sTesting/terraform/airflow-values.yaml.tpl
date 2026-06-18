# Lightweight Airflow: LocalExecutor + git-sync. Heavy/optional components off.
executor: LocalExecutor

# Run DB-migrate and create-user as NORMAL jobs (not Helm hooks). The Terraform
# helm provider doesn't reliably trigger hooks, which left the DB un-migrated.
migrateDatabaseJob:
  useHelmHooks: false
createUserJob:
  useHelmHooks: false

# Use our own postgres:16 (pg.tf) instead of the chart's Bitnami image
# (which was removed from Docker Hub). LocalExecutor needs a real DB.
postgresql:
  enabled: false

data:
  metadataConnection:
    user: airflow
    pass: airflow
    protocol: postgresql
    host: ${pg_host}
    port: 5432
    db: airflow
    sslmode: disable

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

# Literal env applied to every Airflow container.
env:
  - name: _PIP_ADDITIONAL_REQUIREMENTS
    value: "apache-airflow-providers-microsoft-azure"

# extraEnv is rendered verbatim, so it supports valueFrom (the chart's `env`
# schema rejects valueFrom). Pull the wasb connection from the k8s Secret.
extraEnv: |
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
