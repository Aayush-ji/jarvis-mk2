# =============================================================================
# J.A.R.V.I.S. Mk.II — One-Command Server Deployment (Windows PowerShell)
# =============================================================================
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectDir

Write-Host "[JARVIS] Beginning deployment..." -ForegroundColor Cyan

# 1. Prerequisites
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Install from https://python.org"
    exit 1
}

# 2. Environment
if (-not (Test-Path ".env")) {
    Write-Host "[JARVIS] .env not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Please edit .env with your domain and secrets, then re-run this script." -ForegroundColor Yellow
    exit 0
}

# Auto-generate secret if placeholder remains
$envContent = Get-Content ".env" -Raw
if ($envContent -match "replace-with-a-64-character") {
    $secret = [Convert]::ToHexString(([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))).ToLower()
    (Get-Content ".env") -replace "replace-with-a-64-character-hex-secret-string", $secret | Set-Content ".env"
    Write-Host "[JARVIS] Generated JARVIS_SECRET automatically." -ForegroundColor Green
}

# 3. Python environment
Write-Host "[JARVIS] Setting up virtual environment..." -ForegroundColor Cyan
python -m venv venv | Out-Null
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Database initialization
Write-Host "[JARVIS] Initializing database..." -ForegroundColor Cyan
try { python -c "from server import init_db; init_db()" 2>$null } catch { Write-Host "[JARVIS] DB will initialize on first server start." -ForegroundColor Yellow }

# 5. Start server
Write-Host "[JARVIS] Starting JARVIS relay server..." -ForegroundColor Cyan
Start-Process python -ArgumentList "server.py" -WindowStyle Hidden
Write-Host "[JARVIS] Server started in background." -ForegroundColor Green
Write-Host "  - API base:        http://localhost:8765" -ForegroundColor Gray
Write-Host "  - Admin dashboard: http://localhost:8765/dashboard" -ForegroundColor Gray
Write-Host "  - WebSocket:       ws://localhost:8765/ws/{device_id}" -ForegroundColor Gray
Write-Host "" -ForegroundColor Gray
Write-Host "To stop the server: Stop-Process -Name python" -ForegroundColor Yellow
