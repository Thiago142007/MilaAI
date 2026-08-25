$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
.venv\Scripts\playwright install chromium
Write-Host "[NOVA] Chromium instalado para o Playwright." -ForegroundColor Green
