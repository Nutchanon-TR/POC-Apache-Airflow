# Single-node AKS. Control plane on the Free tier = $0; you only pay for the
# one node while it is running. `terraform destroy` (or the 4h auto-stop) ends
# the compute charge.
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = var.aks_name
  sku_tier            = "Free"

  default_node_pool {
    name            = "default"
    node_count      = var.node_count
    vm_size         = var.node_size
    os_disk_size_gb = 32
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    project = "k8s-airflow-poc"
  }
}
