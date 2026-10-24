#!/usr/bin/env bash
# =============================================================================
# J.A.R.V.I.S. Mk.II — Production Keystore Generator
# =============================================================================
set -euo pipefail

KEYSTORE="jarvis_enterprise_signing.keystore"
ALIAS="jarvis"
VALIDITY_DAYS=10000
KEY_SIZE=2048

if [[ -f "$KEYSTORE" ]]; then
  echo "[JARVIS] Keystore $KEYSTORE already exists. Remove it first if you want to regenerate."
  exit 0
fi

echo "[JARVIS] Generating production signing keystore..."
keytool -genkeypair \
  -v \
  -keystore "$KEYSTORE" \
  -alias "$ALIAS" \
  -keyalg RSA \
  -keysize "$KEY_SIZE" \
  -validity "$VALIDITY_DAYS" \
  -dname "CN=JARVIS Mk.II, O=Stark Enterprises, C=US" \
  -storepass:env JARVIS_KEYSTORE_PASS \
  -keypass:env JARVIS_KEY_PASS || \
  keytool -genkeypair \
    -v \
    -keystore "$KEYSTORE" \
    -alias "$ALIAS" \
    -keyalg RSA \
    -keysize "$KEY_SIZE" \
    -validity "$VALIDITY_DAYS" \
    -dname "CN=JARVIS Mk.II, O=Stark Enterprises, C=US"

echo ""
echo "[JARVIS] Keystore created: $KEYSTORE"
echo "[JARVIS] Alias: $ALIAS"
echo "[JARVIS] Store this file securely. Back it up offline."
echo "[JARVIS] Set JARVIS_KEYSTORE_PASS and JARVIS_KEY_PASS environment variables for signing."
