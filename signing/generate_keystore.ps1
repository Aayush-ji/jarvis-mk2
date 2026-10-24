# =============================================================================
# J.A.R.V.I.S. Mk.II — Production Keystore Generator (PowerShell)
# =============================================================================
# Generates an RSA 2048 signing keystore for APK signing.
# Requires Java JDK (keytool) — install via WSL or direct Windows JDK install.
# =============================================================================

$ErrorActionPreference = "Stop"

$KEYSTORE = "signing/jarvis_enterprise_signing.keystore"
$ALIAS = "jarvis"
$VALIDITY_DAYS = 10000
$KEY_SIZE = 2048

# Check for keytool (Java JDK)
if (-not (Get-Command keytool -ErrorAction SilentlyContinue)) {
    Write-Error "keytool not found. Install Java JDK first:"
    Write-Host "  - WSL: sudo apt-get install openjdk-17-jdk"
    Write-Host "  - Windows: https://www.oracle.com/java/technologies/downloads/"
    exit 1
}

# Check for required environment variables
if (-not $env:JARVIS_KEYSTORE_PASS) {
    Write-Error "JARVIS_KEYSTORE_PASS environment variable not set."
    Write-Host "Example: $env:JARVIS_KEYSTORE_PASS = 'your-32-char-hex-password'"
    exit 1
}
if (-not $env:JARVIS_KEY_PASS) {
    Write-Error "JARVIS_KEY_PASS environment variable not set."
    Write-Host "Example: $env:JARVIS_KEY_PASS = 'your-32-char-hex-password'"
    exit 1
}

if (Test-Path $KEYSTORE) {
    Write-Host "[JARVIS] Keystore $KEYSTORE already exists. Remove it first if you want to regenerate." -ForegroundColor Yellow
    exit 0
}

Write-Host "[JARVIS] Generating production signing keystore..." -ForegroundColor Cyan

keytool -genkeypair `
    -v `
    -keystore $KEYSTORE `
    -alias $ALIAS `
    -keyalg RSA `
    -keysize $KEY_SIZE `
    -validity $VALIDITY_DAYS `
    -dname "CN=JARVIS Mk.II, O=Stark Enterprises, C=US" `
    -storepass:$env:JARVIS_KEYSTORE_PASS `
    -keypass:$env:JARVIS_KEY_PASS

Write-Host ""
Write-Host "[JARVIS] Keystore created: $KEYSTORE" -ForegroundColor Green
Write-Host "[JARVIS] Alias: $ALIAS" -ForegroundColor Green
Write-Host "[JARVIS] Store this file securely. Back it up offline." -ForegroundColor Yellow
