# One-click local start: API :8000 + Chat Console :5173 (no Docker)
# Usage (repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "=== KA Cluster local start ==="
Write-Host "Root: $Root"
Write-Host "Precheck: Postgres / Redis ..."

Push-Location $Root
try {
    uv run python scripts/check_local_deps.py
    if ($LASTEXITCODE -ne 0) {
        throw "Local deps not ready. Start PostgreSQL and Memurai/Redis first."
    }
} finally {
    Pop-Location
}

$apiCmd = @"
Set-Location '$Root'
Write-Host '[API] http://127.0.0.1:8000'
uv run uvicorn ka_api.main:app --reload --host 127.0.0.1 --port 8000
"@

$uiCmd = @"
Set-Location '$Root\apps\chat-console'
if (-not (Test-Path 'node_modules')) { npm install }
Write-Host '[UI] http://127.0.0.1:5173'
npm run dev -- --host 127.0.0.1 --port 5173
"@

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $apiCmd)
Start-Sleep -Seconds 1
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $uiCmd)

Write-Host ""
Write-Host "Opened 2 windows:"
Write-Host "  API  -> http://127.0.0.1:8000/docs"
Write-Host "  UI   -> http://127.0.0.1:5173"
Write-Host "Tip: set AUTH_PROVIDER=dev_header in .env for Console user id"
Write-Host "Demo steps: docs/demo-script.md"
