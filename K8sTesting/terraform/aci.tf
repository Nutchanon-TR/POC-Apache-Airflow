locals {
  aci_name = "airflow-aci"

  # Airflow connection (wasb_default) as an env-var connection for WasbBlobSensor.
  wasb_conn_default = jsonencode({
    conn_type = "wasb"
    extra = {
      connection_string = azurerm_storage_account.sa.primary_connection_string
    }
  })

  # Self-stop: sleep N hours, then use the group's OWN managed identity to stop
  # itself. Runs every boot, so `az container start` gives a fresh 4h each time.
  autostop_cmd = join("; ", [
    "sleep ${var.auto_stop_hours * 3600}",
    "az login --identity --allow-no-subscriptions -o none",
    "az container stop --resource-group ${azurerm_resource_group.rg.name} --name ${local.aci_name} --subscription ${var.subscription_id} -o none",
    "echo 'auto-stopped after ${var.auto_stop_hours}h'",
  ])

  # Single-container Airflow: wait for the (sibling) postgres, migrate, create the
  # admin user (idempotent — self-heals after every stop/start since postgres is
  # ephemeral), then run scheduler + webserver together.
  airflow_cmd = <<-EOT
    set -e
    pip install --no-cache-dir "apache-airflow-providers-microsoft-azure"
    until airflow db check >/dev/null 2>&1; do echo "waiting for db..."; sleep 3; done
    airflow db migrate
    airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com || true
    airflow scheduler &
    exec airflow webserver
  EOT
}

# Plain container on Azure (no Kubernetes). One container group = postgres +
# airflow sharing localhost; DAGs come from the mounted file share.
resource "azurerm_container_group" "airflow" {
  name                = local.aci_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"
  restart_policy      = "OnFailure"
  ip_address_type     = "Public"
  dns_name_label      = "${var.prefix}${random_string.suffix.result}"

  # Managed identity the self-stop sidecar uses to stop this group.
  identity {
    type = "SystemAssigned"
  }

  # ── metadata DB (ephemeral; LocalExecutor needs a real DB for parallelism) ──
  container {
    name   = "postgres"
    image  = "postgres:16"
    cpu    = 0.5
    memory = 1.0

    environment_variables = {
      POSTGRES_USER = "airflow"
      POSTGRES_DB   = "airflow"
    }
    secure_environment_variables = {
      POSTGRES_PASSWORD = "airflow"
    }

    # No ports block: postgres is reached only via localhost inside the group,
    # never exposed on the public IP.
  }

  # ── Airflow (scheduler + webserver, LocalExecutor) ──────────────────────────
  container {
    name     = "airflow"
    image    = var.airflow_image
    cpu      = 1.0
    memory   = 2.0
    commands = ["/bin/bash", "-c", local.airflow_cmd]

    environment_variables = {
      AIRFLOW__CORE__EXECUTOR             = "LocalExecutor"
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN = "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow"
      AIRFLOW__CORE__LOAD_EXAMPLES        = "False"
      AIRFLOW__WEBSERVER__SECRET_KEY      = "airflow-aci-poc-secret"
      AIRFLOW_HOME                        = "/opt/airflow"
      HELLO_BLOB_CONTAINER                = var.blob_container_name
    }
    secure_environment_variables = {
      AIRFLOW_CONN_WASB_DEFAULT       = local.wasb_conn_default
      AZURE_STORAGE_CONNECTION_STRING = azurerm_storage_account.sa.primary_connection_string
    }

    ports {
      port     = 8080
      protocol = "TCP"
    }

    volume {
      name                 = "dags"
      mount_path           = "/opt/airflow/dags"
      share_name           = azurerm_storage_share.dags.name
      storage_account_name = azurerm_storage_account.sa.name
      storage_account_key  = azurerm_storage_account.sa.primary_access_key
    }
  }

  # ── self-stop sidecar (auto-stop after N hours) ─────────────────────────────
  container {
    name     = "autostop"
    image    = "mcr.microsoft.com/azure-cli:latest"
    cpu      = 0.2
    memory   = 0.5
    commands = ["/bin/bash", "-c", local.autostop_cmd]
  }

  tags = {
    project = "airflow-aci-poc"
  }

  depends_on = [azurerm_storage_share_file.dag]
}
