# Storage account + container for:
#   - DAG 00/01/03/04: the "drop a Hello file" job uploads here
#   - DAG 06: WasbBlobSensor polls this container for a blob
resource "azurerm_storage_account" "sa" {
  name                     = "${var.prefix}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = {
    project = "k8s-airflow-poc"
  }
}

resource "azurerm_storage_container" "hello" {
  name                  = var.blob_container_name
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"
}
