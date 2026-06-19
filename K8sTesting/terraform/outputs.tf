output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "container_group" {
  value = azurerm_container_group.airflow.name
}

output "storage_account" {
  value = azurerm_storage_account.sa.name
}

output "blob_container" {
  value = azurerm_storage_container.hello.name
}

output "airflow_ui_url" {
  description = "Airflow UI (login admin/admin)."
  value       = "http://${azurerm_container_group.airflow.fqdn}:8080"
}

output "auto_stop_after" {
  description = "Container group self-stops this many hours after each start."
  value       = "${var.auto_stop_hours}h"
}

output "manual_start_cmd" {
  value = "az container start --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_container_group.airflow.name}"
}

output "manual_stop_cmd" {
  value = "az container stop --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_container_group.airflow.name}"
}
