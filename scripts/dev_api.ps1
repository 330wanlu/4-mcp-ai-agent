# Start FastAPI (:8000). Default ORCHESTRATOR_MODE=local (no separate orchestrator).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "[dev_api] http://127.0.0.1:8000  (docs: /docs)"
uv run uvicorn ka_api.main:app --reload --host 127.0.0.1 --port 8000
