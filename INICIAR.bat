@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title MILA 3D VTuber AI

if not exist "node_modules" (
    echo [MILA] Instalando dependencias do Node.js e Three.js...
    call npm install
)

if not exist ".venv" (
    echo [MILA] Criando ambiente virtual Python...
    py -m venv .venv 2>nul || python -m venv .venv
)

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import kokoro_onnx, soundfile, numpy" >nul 2>&1
    if errorlevel 1 (
        echo [MILA] Instalando dependencias de IA e Voz local Kokoro-82M...
        call .venv\Scripts\pip.exe install -r requirements.txt
    )
)

if not exist ".env" (
    echo [MILA] Criando arquivo .env...
    copy /y ".env.example" ".env" >nul
)

echo [MILA] Verificando e liberando porta 8765...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [MILA] Iniciando servidor e abrindo interface 3D...
start "" "http://127.0.0.1:8765"
call npm run dev
if errorlevel 1 (
    echo [MILA] Ocorreu um erro ao executar o servidor.
    pause
)
