# Bring the stack up (RG + storage + file share + Airflow container + 4h auto-stop).
# Usage:  .\up.ps1
$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\terraform"
try {
    terraform init -input=false
    terraform apply -auto-approve
    Write-Host "`n=== Airflow UI (admin/admin) ===" -ForegroundColor Cyan
    terraform output -raw airflow_ui_url; Write-Host ""
    Write-Host "Self-stops after: " -NoNewline
    terraform output -raw auto_stop_after; Write-Host ""
}
finally {
    Pop-Location
}
