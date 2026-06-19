# Brand-new resource group for the whole POC. `terraform destroy` removes it
# (and everything inside) so we go back to $0.
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    project    = "airflow-aci-poc"
    managed_by = "terraform"
  }
}

# Random suffix to keep storage account name + DNS label globally unique.
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}
