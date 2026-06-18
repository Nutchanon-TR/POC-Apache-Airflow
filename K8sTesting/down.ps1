# Tear everything down -> back to $0. Usage:  .\down.ps1
$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\terraform"
try {
    terraform destroy -auto-approve
}
finally {
    Pop-Location
}
