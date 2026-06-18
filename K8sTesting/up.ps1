# Bring the whole stack up (RG + AKS + storage + Airflow + 4h auto-stop).
# Usage:  .\up.ps1
$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\terraform"
try {
    terraform init -input=false
    terraform apply -auto-approve
    Write-Host "`n=== Connect ===" -ForegroundColor Cyan
    terraform output -raw get_credentials_cmd; Write-Host ""
    terraform output -raw airflow_ui_cmd; Write-Host ""
    Write-Host "Auto-stop at (UTC): " -NoNewline
    terraform output -raw auto_stop_at_utc; Write-Host ""
}
finally {
    Pop-Location
}
