locals {
  # Airflow connection (wasb_default) injected as an env-var connection.
  # The Azure provider's WasbHook reads `connection_string` from extra.
  wasb_conn_default = jsonencode({
    conn_type = "wasb"
    extra = {
      connection_string = azurerm_storage_account.sa.primary_connection_string
    }
  })
}

resource "kubernetes_namespace" "airflow" {
  metadata {
    name = "airflow"
  }
}

# Secret consumed two ways:
#   - Airflow scheduler/webserver: AIRFLOW_CONN_WASB_DEFAULT (for WasbBlobSensor)
#   - KPO worker pods: AZURE_STORAGE_CONNECTION_STRING (for `az storage blob upload`)
resource "kubernetes_secret" "azure_storage" {
  metadata {
    name      = "azure-storage"
    namespace = kubernetes_namespace.airflow.metadata[0].name
  }

  data = {
    AZURE_STORAGE_CONNECTION_STRING = azurerm_storage_account.sa.primary_connection_string
    AZURE_STORAGE_ACCOUNT           = azurerm_storage_account.sa.name
    AIRFLOW_CONN_WASB_DEFAULT       = local.wasb_conn_default
  }

  type = "Opaque"
}

# ── RBAC so the scheduler (LocalExecutor runs tasks in-process) can launch the
#    KubernetesPodOperator pods via in_cluster config ─────────────────────────
resource "kubernetes_service_account" "kpo" {
  metadata {
    name      = "airflow-kpo"
    namespace = kubernetes_namespace.airflow.metadata[0].name
  }
}

resource "kubernetes_role" "kpo" {
  metadata {
    name      = "airflow-kpo-pod-launcher"
    namespace = kubernetes_namespace.airflow.metadata[0].name
  }

  rule {
    api_groups = [""]
    resources  = ["pods", "pods/log", "pods/exec"]
    verbs      = ["get", "list", "watch", "create", "delete", "patch"]
  }
}

resource "kubernetes_role_binding" "kpo" {
  metadata {
    name      = "airflow-kpo-pod-launcher"
    namespace = kubernetes_namespace.airflow.metadata[0].name
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.kpo.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.kpo.metadata[0].name
    namespace = kubernetes_namespace.airflow.metadata[0].name
  }
}

# ── Airflow via the official Helm chart, overridden to a lightweight
#    LocalExecutor + git-sync setup ────────────────────────────────────────────
resource "helm_release" "airflow" {
  name       = "airflow"
  namespace  = kubernetes_namespace.airflow.metadata[0].name
  repository = "https://airflow.apache.org"
  chart      = "airflow"
  version    = var.airflow_chart_version

  # First boot pulls images + pip-installs the azure provider, so give it room.
  timeout = 1200
  wait    = true

  values = [
    templatefile("${path.module}/airflow-values.yaml.tpl", {
      git_repo      = var.git_repo_url
      git_branch    = var.git_branch
      git_subpath   = var.git_subpath
      kpo_sa        = kubernetes_service_account.kpo.metadata[0].name
      secret_name   = kubernetes_secret.azure_storage.metadata[0].name
    })
  ]

  depends_on = [
    kubernetes_role_binding.kpo,
    kubernetes_secret.azure_storage,
  ]
}
