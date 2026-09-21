Clear-Host
$ProjectDir = $PSScriptRoot

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "               ARK KNOWLEDGE GATEWAY INITIALIZATION TERMINAL        " -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# --- VIRTUAL ENVIRONMENT AUTOMATION LAYER ---
$VenvPath = Join-Path $ProjectDir ".venv"

if (-not (Test-Path $VenvPath)) {
    Write-Host "[!] Target environment container (.venv) not found." -ForegroundColor Yellow
    Write-Host "[*] Provisioning isolated runtime engine..." -ForegroundColor Yellow

    Set-Location $ProjectDir
    python -m venv .venv

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] ERROR: Python execution failed. Verify Python is added to your System PATH variables." -ForegroundColor Red
        Pause
        Exit
    }

    & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
} else {
    Write-Host "[+] Verified localized runtime container consistency (.venv active)." -ForegroundColor Green
}

# Always re-synced, not just on first creation — otherwise a requirements.txt change (a new
# dependency, a version bump) silently never reaches an already-existing .venv, and the app
# only fails at import time with no hint that a stale environment was the cause.
Write-Host "[*] Syncing enterprise dependencies from requirements.txt..." -ForegroundColor Yellow
& ".\.venv\Scripts\pip.exe" install -r requirements.txt --quiet
Write-Host "[+] Secure boundary packages up to date!`n" -ForegroundColor Green

# --- APPLICATION ORCHESTRATION LAYER ---

# 1. Start the FastAPI Backend Engine (Port 8000)
Write-Host "[*] Launching FastAPI Security Backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'ARK Backend (FastAPI)'; cd '$ProjectDir'; .\.venv\Scripts\uvicorn app:app --reload --port 8002"

# Small delay to let the backend bind ports cleanly
Start-Sleep -Seconds 2

# 2. Start the Vite Frontend Server (Forced onto 127.0.0.1:8080)
Write-Host "[*] Launching Vite Frontend Development Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'ARK Frontend (Vite)'; cd 'local'; npm run dev -- --host 127.0.0.1 --port 8081"

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "   SUCCESS: Both engine cores active in separate system instances!   " -ForegroundColor Green
Write-Host "   - Backend: http://127.0.0.1:8002" -ForegroundColor Green
Write-Host "   - Frontend: http://127.0.0.1:8081" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host ""