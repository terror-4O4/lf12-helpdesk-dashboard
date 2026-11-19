# Startet das Backend unter Windows. Aufruf aus dem Repo-Hauptordner:
#   .\scripts\start-backend.ps1
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
    Write-Host "Fehlt: .env  ->  Copy-Item .env.example .env"
    exit 1
}

if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

# Host und Port aus der .env lesen (Standard: nur lokal erreichbar)
$appHost = "127.0.0.1"
$appPort = "8000"
foreach ($zeile in Get-Content ".env") {
    if ($zeile -match '^APP_HOST=(.+)$') { $appHost = $Matches[1].Trim() }
    if ($zeile -match '^APP_PORT=(.+)$') { $appPort = $Matches[1].Trim() }
}

uvicorn backend.app:app --reload --host $appHost --port $appPort
