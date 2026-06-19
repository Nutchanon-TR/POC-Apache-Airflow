# Storage account holds:
#   - blob container "hello-demo": upload task target + WasbBlobSensor source
#   - file share "dags": mounted into the Airflow container as the DAGs folder
resource "azurerm_storage_account" "sa" {
  name                     = "${var.prefix}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = {
    project = "airflow-aci-poc"
  }
}

resource "azurerm_storage_container" "hello" {
  name                  = var.blob_container_name
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"
}

resource "azurerm_storage_share" "dags" {
  name                 = "dags"
  storage_account_name = azurerm_storage_account.sa.name
  quota                = 1
}

# Upload every DAG file from ../dags onto the file share. Changing a DAG locally
# re-uploads it on the next apply (content_md5 triggers the update).
resource "azurerm_storage_share_file" "dag" {
  for_each = fileset("${path.module}/../dags", "*.py")

  name             = each.value
  storage_share_id = azurerm_storage_share.dags.id
  source           = "${path.module}/../dags/${each.value}"
  content_md5      = filemd5("${path.module}/../dags/${each.value}")
}
