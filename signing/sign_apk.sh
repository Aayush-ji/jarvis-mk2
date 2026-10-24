#!/usr/bin/env bash
# =============================================================================
# J.A.R.V.I.S. Mk.II — APK Signing & Zipalign
# =============================================================================
set -euo pipefail

APK_INPUT="${1:-bin/jarvis-2.0.0.apk}"
APK_OUTPUT="${2:-bin/jarvis-mk2-release.apk}"
KEYSTORE="${KEYSTORE:-jarvis_enterprise_signing.keystore}"
ALIAS="${ALIAS:-jarvis}"

if [[ ! -f "$APK_INPUT" ]]; then
  echo "Input APK not found: $APK_INPUT"
  echo "Build it first with: buildozer -v android debug"
  exit 1
fi

if [[ ! -f "$KEYSTORE" ]]; then
  echo "Keystore not found: $KEYSTORE"
  echo "Run: ./signing/generate_keystore.sh"
  exit 1
fi

if [[ -z "${JARVIS_KEYSTORE_PASS:-}" || -z "${JARVIS_KEY_PASS:-}" ]]; then
  echo "Set JARVIS_KEYSTORE_PASS and JARVIS_KEY_PASS environment variables."
  exit 1
fi

echo "[JARVIS] Aligning APK..."
zipalign -v -p 4 "$APK_INPUT" "$APK_OUTPUT.aligned"

echo "[JARVIS] Signing APK..."
apksigner sign \
  --ks "$KEYSTORE" \
  --ks-key-alias "$ALIAS" \
  --ks-pass "env:JARVIS_KEYSTORE_PASS" \
  --key-pass "env:JARVIS_KEY_PASS" \
  --out "$APK_OUTPUT" \
  "$APK_OUTPUT.aligned"

rm -f "$APK_OUTPUT.aligned"

echo ""
echo "[JARVIS] Production APK ready: $APK_OUTPUT"
echo "[JARVIS] Verify: apksigner verify --print-certs $APK_OUTPUT"
