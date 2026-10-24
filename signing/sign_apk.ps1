# =============================================================================
# J.A.R.V.I.S. Mk.II — APK Signing & Zipalign (PowerShell)
# =============================================================================
# Requires: zipalign, apksigner (Android SDK build-tools) and Java JDK
# =============================================================================

$ErrorActionPreference = "Stop"

$APK_INPUT  = if ($args.Count -gt 0) { $args[0] } else { "bin/jarvis-2.0.0.apk" }
$APK_OUTPUT = if ($args.Count -gt 1) { $args[1] } else { "bin/jarvis-mk2-release.apk" }
$KEYSTORE   = if ($env:KEYSTORE) { $env:KEYSTORE } else { "signing/jarvis_enterprise_signing.keystore" }
$ALIAS      = if ($env:ALIAS) { $env:ALIAS } else { "jarvis" }

if (-not (Test-Path $APK_INPUT)) {
    Write-Error "Input APK not found: $APK_INPUT"
    Write-Host "Build it first with: buildozer -v android debug" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $KEYSTORE)) {
    Write-Error "Keystore not found: $KEYSTORE"
    Write-Host "Run: .\signing\generate_keystore.ps1" -ForegroundColor Yellow
    exit 1
}

if (-not $env:JARVIS_KEYSTORE_PASS -or -not $env:JARVIS_KEY_PASS) {
    Write-Error "JARVIS_KEYSTORE_PASS and JARVIS_KEY_PASS must be set."
    exit 1
}

# Check for apksigner and zipalign
if (-not (Get-Command apksigner -ErrorAction SilentlyContinue) -or -not (Get-Command zipalign -ErrorAction SilentlyContinue)) {
    Write-Error "apksigner or zipalign not found. Install Android SDK build-tools."
    exit 1
}

Write-Host "[JARVIS] Aligning APK..." -ForegroundColor Cyan
& zipalign -v -p 4 $APK_INPUT "$APK_OUTPUT.aligned"

Write-Host "[JARVIS] Signing APK..." -ForegroundColor Cyan
& apksigner sign `
    --ks $KEYSTORE `
    --ks-key-alias $ALIAS `
    --ks-pass "pass:$env:JARVIS_KEYSTORE_PASS" `
    --key-pass "pass:$env:JARVIS_KEY_PASS" `
    --out $APK_OUTPUT `
    "$APK_OUTPUT.aligned"

if (Test-Path "$APK_OUTPUT.aligned") { Remove-Item "$APK_OUTPUT.aligned" }

Write-Host ""
Write-Host "[JARVIS] Production APK ready: $APK_OUTPUT" -ForegroundColor Green
Write-Host "[JARVIS] Verify: apksigner verify --print-certs $APK_OUTPUT" -ForegroundColor Gray
