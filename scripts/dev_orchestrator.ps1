# Optional: standalone Orchestrator (:8001). Set ORCHESTRATOR_MODE=http on API side.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "[dev_orchestrator] http://127.0.0.1:8001"
uv run uvicorn ka_orchestrator.main:app --reload --host 127.0.0.1 --port 8001
