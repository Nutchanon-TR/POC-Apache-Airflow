$ErrorActionPreference = "Stop"

# Token from the Automation account's system-assigned managed identity.
# Uses the local identity endpoint, so no Az PowerShell module import is needed.
$resource = "https://management.azure.com/"
$tokenUri = "$($env:IDENTITY_ENDPOINT)?resource=$resource&api-version=2019-08-01"
$tokenResp = Invoke-RestMethod -Method Get -Uri $tokenUri -Headers @{ "X-IDENTITY-HEADER" = $env:IDENTITY_HEADER; "Metadata" = "true" }
$token = $tokenResp.access_token

# Deallocate the AKS node(s): compute charge stops, cluster + data are kept.
$stopUri = "https://management.azure.com/subscriptions/${subscription_id}/resourceGroups/${rg}/providers/Microsoft.ContainerService/managedClusters/${aks}/stop?api-version=2024-09-01"
Invoke-RestMethod -Method Post -Uri $stopUri -Headers @{ Authorization = "Bearer $token" }
Write-Output "AKS stop request sent for ${aks}."
