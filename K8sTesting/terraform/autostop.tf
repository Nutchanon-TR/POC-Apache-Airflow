# ── Auto-stop safety net ─────────────────────────────────────────────────────
# If you forget to `terraform destroy`, an Azure Automation runbook stops the
# AKS node(s) `auto_stop_hours` after apply, so credit stops bleeding even with
# your laptop off. `az aks start` (or another apply) brings it back in ~1 min.

resource "azurerm_automation_account" "auto" {
  name                = "${var.prefix}-autostop"
  location            = var.automation_location
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = "Basic"

  identity {
    type = "SystemAssigned"
  }
}

# Let the runbook's identity stop the AKS cluster in this RG.
resource "azurerm_role_assignment" "auto_contributor" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_automation_account.auto.identity[0].principal_id
}

resource "azurerm_automation_runbook" "stop_aks" {
  name                    = "stop-aks"
  location                = var.automation_location
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.auto.name
  log_verbose             = false
  log_progress            = false
  description             = "Stops the POC AKS cluster to save credit."
  runbook_type            = "PowerShell"

  content = templatefile("${path.module}/stop-aks.ps1.tpl", {
    subscription_id = var.subscription_id
    rg              = azurerm_resource_group.rg.name
    aks             = azurerm_kubernetes_cluster.aks.name
  })
}

resource "azurerm_automation_schedule" "in_n_hours" {
  name                    = "stop-after-${var.auto_stop_hours}h"
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.auto.name
  frequency               = "OneTime"
  timezone                = "Etc/UTC"
  start_time              = timeadd(timestamp(), "${var.auto_stop_hours}h")

  # start_time is computed from apply time; don't let a later plan force replace.
  lifecycle {
    ignore_changes = [start_time]
  }
}

resource "azurerm_automation_job_schedule" "stop_link" {
  resource_group_name     = azurerm_resource_group.rg.name
  automation_account_name = azurerm_automation_account.auto.name
  runbook_name            = azurerm_automation_runbook.stop_aks.name
  schedule_name           = azurerm_automation_schedule.in_n_hours.name
}
