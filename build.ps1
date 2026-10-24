# =============================================================================
# J.A.R.V.I.S. Mk.II — APK Build & Sign Orchestrator (PowerShell)
# =============================================================================
# Walks through: Keystore generation → Buildozer APK build → APK signing
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  J.A.R.V.I.S. Mk.II — APK Build & Sign Pipeline" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# --- Keystore Passwords (generated automatically) ---
$KEYSTORE_PASS = "3229483C65C7A6E39545008ACB816C1F"
$KEY_PASS      = "E1A8DADA30910928F48D6DCCABD18B41"

Write-Host "[1/4] Keystore credentials:" -ForegroundColor Yellow
Write-Host "  JARVIS_KEYSTORE_PASS = $KEYSTORE_PASS" -ForegroundColor Gray
Write-Host "  JARVIS_KEY_PASS      = $KEY_PASS" -ForegroundColor Gray
Write-Host ""

# --- Step 1: Generate Keystore ---
Write-Host "[2/4] Generating production keystore..." -ForegroundColor Cyan
$env:JARVIS_KEYSTORE_PASS = $KEYSTORE_PASS
$env:JARVIS_KEY_PASS = $KEY_PASS
if (-not (Get-Command keytool -ErrorAction SilentlyContinue)) {
    Write-Host "  [SKIP] keytool not found. Install Java JDK first:" -ForegroundColor Yellow
    Write-Host "    WSL:   sudo apt-get install openjdk-17-jdk" -ForegroundColor Gray
    Write-Host "    Win:   https://www.oracle.com/java/technologies/downloads/" -ForegroundColor Gray
    Write-Host "  Then re-run: .\signing\generate_keystore.ps1" -ForegroundColor Gray
} else {
    & .\signing\generate_keystore.ps1
}
Write-Host ""

# --- Step 2: Check Buildozer ---
Write-Host "[3/4] Checking build environment..." -ForegroundColor Cyan
if (-not (Get-Command buildozer -ErrorAction SilentlyContinue)) {
    Write-Host "  [SKIP] buildozer not found." -ForegroundColor Yellow
    Write-Host "  Install via WSL:" -ForegroundColor Gray
    Write-Host "    wsl --install" -ForegroundColor Gray
    Write-Host "    sudo apt-get update && sudo apt-get install -y openjdk-17-jdk unzip zip python3-pip" -ForegroundColor Gray
    Write-Host "    pip3 install buildozer cython" -ForegroundColor Gray
    Write-Host "    cd /mnt/c/Users/window\ 11/jarvis_enterprise" -ForegroundColor Gray
    Write-Host "    buildozer -v android debug" -ForegroundColor Gray
} else {
    Write-Host "  Buildozer found. Building APK..." -ForegroundColor Gray
    & buildozer -v android debug
}
Write-Host ""

# --- Step 3: Sign APK ---
Write-Host "[4/4] Signing APK..." -ForegroundColor Cyan
$APK = "bin/jarvis-2.0.0.apk"
$OUT = "bin/jarvis-mk2-release.apk"
if (-not (Test-Path $APK)) {
    Write-Host "  [SKIP] APK not found at $APK. Build it first." -ForegroundColor Yellow
} else {
    $env:JARVIS_KEYSTORE_PASS = $KEYSTORE_PASS
    $env:JARVIS_KEY_PASS = $KEY_PASS
    & .\signing\sign_apk.ps1 $APK $OUT
}
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Pipeline complete. See README_DEPLOY.md for next steps." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
