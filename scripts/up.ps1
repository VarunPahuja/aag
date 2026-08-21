# PowerShell equivalent of `make up`, for teammates without GNU make.
# Usage: .\scripts\up.ps1

docker compose up -d --wait db adminer
Write-Host "db ready on localhost:5432 - Adminer on http://localhost:8080"
