# 启动 Chat Console（需另开终端启动 API :8000）
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\apps\chat-console")
if (-not (Test-Path "node_modules")) {
    npm install
}
npm run dev
