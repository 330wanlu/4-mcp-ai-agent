# Start Chat Console (start API :8000 in another terminal first).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\apps\chat-console")
if (-not (Test-Path "node_modules")) {
    npm install
}
npm run dev
