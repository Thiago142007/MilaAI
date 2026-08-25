$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

if (-not (Test-Path "node_modules")) {
  Write-Host "[NOVA] Instalando dependencias do Node.js e Three.js..." -ForegroundColor Cyan
  npm install
}

if (-not (Test-Path ".env")) {
  if (Test-Path ".env.example") {
    Copy-Item ".env.example" ".env"
  }
}

Write-Host "[NOVA] Abrindo interface 3D da NOVA..." -ForegroundColor Green
Start-Process "http://127.0.0.1:8765"
npm run dev
