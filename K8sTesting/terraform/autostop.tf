# ── Auto-stop safety net ─────────────────────────────────────────────────────
# The container group self-stops after `auto_stop_hours` (see the "autostop"
# sidecar in aci.tf). That sidecar uses the group's system-assigned managed
# identity, which needs permission to stop the group — grant Contributor on the
# resource group here. Runs even with your laptop off; resets on every start.
resource "azurerm_role_assignment" "self_stop" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_container_group.airflow.identity[0].principal_id
}
