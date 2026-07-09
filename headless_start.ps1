Clear-Host
$ProjectDir = $PSScriptRoot

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "               PAAPP HEADLESS TOOL HUB INITIALIZATION TERMINAL       " -ForegroundColor Cyan
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
    
    Write-Host "[*] Syncing enterprise dependencies from requirements.txt..." -ForegroundColor Yellow
    & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    & ".\.venv\Scripts\pip.exe" install -r requirements.txt
    
    Write-Host "[+] Secure boundary packages initialized successfully!`n" -ForegroundColor Green
} else {
    Write-Host "[+] Verified localized runtime container consistency (.venv active)." -ForegroundColor Green
}

# --- APPLICATION ORCHESTRATION LAYER ---

Write-Host "[*] Launching PAAPP Headless Tool Hub (FastAPI)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'PAAPP Headless (FastAPI)'; cd '$ProjectDir'; .\.venv\Scripts\uvicorn headless_app:app --reload --port 8003"

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "   SUCCESS: PAAPP Headless Tool Hub is now active!                    " -ForegroundColor Green
Write-Host "   - Headless API: http://127.0.0.1:8003/docs                         " -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host ""
