output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "aks_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "storage_account" {
  value = azurerm_storage_account.sa.name
}

output "blob_container" {
  value = azurerm_storage_container.hello.name
}

output "get_credentials_cmd" {
  description = "Merge AKS creds into your local kubeconfig."
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_kubernetes_cluster.aks.name} --overwrite-existing"
}

output "airflow_ui_cmd" {
  description = "Port-forward the Airflow UI to http://localhost:8080 (login admin/admin)."
  value       = "kubectl -n airflow port-forward svc/airflow-webserver 8080:8080"
}

output "auto_stop_at_utc" {
  description = "When the cluster will be auto-stopped (UTC)."
  value       = azurerm_automation_schedule.in_n_hours.start_time
}

output "manual_start_cmd" {
  value = "az aks start --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_kubernetes_cluster.aks.name}"
}

output "manual_stop_cmd" {
  value = "az aks stop --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_kubernetes_cluster.aks.name}"
}
