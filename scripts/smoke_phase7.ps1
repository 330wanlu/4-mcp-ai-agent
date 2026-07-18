# Phase 7 smoke: deps -> demo_cli (timed) -> optional full pytest
# Usage:
#   powershell -File scripts\smoke_phase7.ps1
#   powershell -File scripts\smoke_phase7.ps1 -SkipPytest
param(
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host "=== Phase 7 smoke ==="
$swTotal = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host "`n[1/3] check_local_deps"
uv run python scripts/check_local_deps.py
if ($LASTEXITCODE -ne 0) { throw "deps failed" }

Write-Host "`n[2/3] demo_cli (default question)"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
uv run python scripts/demo_cli.py
$demoCode = $LASTEXITCODE
$sw.Stop()
Write-Host ("DEMO_CLI_SECONDS={0:N1}" -f $sw.Elapsed.TotalSeconds)
if ($demoCode -ne 0) { throw "demo_cli failed" }

if (-not $SkipPytest) {
    Write-Host "`n[3/3] pytest -q (full suite, may take several minutes)"
    $sw2 = [System.Diagnostics.Stopwatch]::StartNew()
    uv run pytest -q --tb=line
    $pytestCode = $LASTEXITCODE
    $sw2.Stop()
    Write-Host ("PYTEST_SECONDS={0:N1}" -f $sw2.Elapsed.TotalSeconds)
    if ($pytestCode -ne 0) { throw "pytest failed" }
} else {
    Write-Host "`n[3/3] pytest skipped (-SkipPytest)"
}

$swTotal.Stop()
Write-Host ("`nPHASE7_SMOKE_OK total_seconds={0:N1}" -f $swTotal.Elapsed.TotalSeconds)
exit 0
