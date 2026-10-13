# =========================================================
# Study Activity Tracker - One-Click Launcher for PowerShell
# =========================================================

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   Starting Study Activity Tracker       " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$RootDir = $PSScriptRoot

# 1. Launch Backend in a dedicated PowerShell window
Write-Host "`n[1/2] Launching Backend (FastAPI on http://127.0.0.1:8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "Set-Location '$RootDir\backend'; if (Test-Path 'venv\Scripts\Activate.ps1') { & '.\venv\Scripts\Activate.ps1' } else { python -m venv venv; & '.\venv\Scripts\Activate.ps1'; pip install -r requirements.txt }; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

# 2. Launch Frontend in a dedicated PowerShell window
Write-Host "[2/2] Launching Frontend (Vite on http://127.0.0.1:5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$RootDir\frontend'; if (-not (Test-Path 'node_modules')) { npm install }; npm run dev"

Write-Host "`nBoth services are starting in separate windows!" -ForegroundColor Yellow
Write-Host "• Frontend UI: http://localhost:5173" -ForegroundColor Cyan
Write-Host "• Backend API: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "`nPress any key to exit this launcher window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
