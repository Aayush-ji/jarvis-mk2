# J.A.R.V.I.S. Mk.II — Deployment & Release Guide

## Phase 1: Backend Deployment ✅ COMPLETE

The relay server is running locally at `http://localhost:8765`. The laptop agent is connected and all plugins are loaded.

### Current Status
| Component | Status |
|---|---|
| Relay Server | ✅ Running on `ws://localhost:8765/ws` |
| Health Endpoint | ✅ `{"status": "ok", "version": "2.0.0"}` |
| Device Enrollment | ✅ Laptop enrolled (device_id: `laptop`) |
| Laptop Agent | ✅ Connected, 6 plugins loaded |
| Voice Intent Router | ✅ Tested — all commands route correctly |
| `.env` | ✅ Configured with JARVIS_SECRET and LAPTOP_TOKEN |

### `.env` (Current Values)
```
JARVIS_SECRET=B16EBCA9F0415A8C3AC46E02A7FFC1BA11CBFCCBC61602278C5AAD8829629D1D
SERVER_URL=ws://localhost:8765/ws
LAPTOP_DEVICE_ID=laptop
LAPTOP_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJsYXB0b3AiLCJleHAiOjE3OTUxMDc3NTF9.aGKCUQosX7hdlIoHmw8x_Ue0iimu8IvLBIoXXMOL5vc
ALLOWED_IPS=127.0.0.1,::1
DOMAIN=jarvis.yourdomain.com   # Change for production WSS
```

---

## Phase 2: Mobile Client — APK Build & Sign (Options 3 & 4)

### Keystore Credentials (Generated)

| Variable | Value |
|---|---|
| `JARVIS_KEYSTORE_PASS` | `3229483C65C7A6E39545008ACB816C1F` |
| `JARVIS_KEY_PASS` | `E1A8DADA30910928F48D6DCCABD18B41` |

**Save these securely.** They are required to sign the APK and cannot be recovered if lost.

### Prerequisites (Windows)

Buildozer does not run natively on Windows. You need **WSL (Windows Subsystem for Linux)** with Java JDK and Android SDK:

```powershell
# 1. Install WSL (one-time)
wsl --install
# Restart Windows when prompted

# 2. Open WSL (Ubuntu) and install dependencies
wsl
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk unzip zip python3-pip git
pip3 install buildozer cython

# 3. Navigate to the project
cd /mnt/c/Users/window\ 11/jarvis_enterprise

# 4. Build the debug APK
buildozer -v android debug
```

### Step-by-Step Build & Sign

```powershell
# Set keystore passwords (required for signing)
$env:JARVIS_KEYSTORE_PASS = "3229483C65C7A6E39545008ACB816C1F"
$env:JARVIS_KEY_PASS = "E1A8DADA30910928F48D6DCCABD18B41"

# Generate keystore (requires keytool/Java)
.\signing\generate_keystore.ps1

# Build APK via WSL (see prerequisites above)
# Output: bin/jarvis-2.0.0.apk

# Sign the APK
.\signing\sign_apk.ps1 bin/jarvis-2.0.0.apk bin/jarvis-mk2-release.apk

# Verify signature
apksigner verify --print-certs bin/jarvis-mk2-release.apk
```

### One-Command Pipeline

```powershell
.\build.ps1
```

This orchestrates keystore generation → build environment check → APK signing.

### Configure the APK Client

Before building, edit `android_client/main.py`:

```python
SERVER_URL = "wss://YOUR_DOMAIN/ws"   # Production WSS URL
DEVICE_ID = "phone"
TOKEN = ""  # Get from: POST http://localhost:8765/auth/enroll
```

Then enroll the phone device:
```bash
curl -X POST http://localhost:8765/auth/enroll \
  -d 'device_id=phone&name=Executive Phone&platform=android'
```

### APK Features

| Feature | Description |
|---|---|
| Encrypted file transfer | X25519 + AES-256-GCM E2EE with resume |
| Foreground service | Persistent WebSocket connection (survives screen lock) |
| Biometric unlock | Optional gate before file decryption |
| App shortcuts | Send File, System Status, Remote Shell |
| Splash screen | Professional cold-start branding |
| Adaptive icon | Android adaptive launcher icon |

---

## Phase 3: Production SSL (Before Client Onboarding)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d jarvis.yourdomain.com

# Update nginx/jarvis.conf with SSL paths
# Restart nginx
sudo systemctl restart nginx
```

---

## File Inventory

```
jarvis_enterprise/
├── .env                          # Configuration (JWT secret, tokens, URLs)
├── .env.example                  # Template
├── server.py                     # Enterprise relay (JWT, WebSocket, REST, audit)
├── crypto.py                     # X25519 + AES-256-GCM encryption
├── jarvis_client.py              # Base client (WebSocket, plugins, acks)
├── laptop_plugins.py             # 6 plugins: sysinfo, shell, say, screenshot, open, file_transfer
├── run_laptop.py                 # Desktop agent entry point
├── voice_interface.py            # Wake-word STT/TTS + intent router
├── requirements.txt              # Python dependencies
├── deploy.ps1                    # Windows deployment script
├── deploy.sh                     # Linux/macOS deployment script
├── docker-compose.yml            # Container stack (relay + Redis + Nginx)
├── Dockerfile                    # Production container image
├── build.ps1                     # APK build & sign orchestrator
├── buildozer.spec                # Android APK build profile
├── dashboard/index.html          # Executive command console
├── nginx/jarvis.conf             # WSS reverse proxy
├── systemd/jarvis.service        # Hardened systemd unit
├── android_client/main.py        # Kivy APK client
├── android/AndroidManifest_ext.xml
├── android/res/drawable/splash.xml
├── android/res/mipmap-anydpi-v26/ic_launcher.xml
├── android/res/values/shortcuts.xml
├── signing/generate_keystore.ps1 # Keystore generator (PowerShell)
├── signing/sign_apk.ps1          # APK signing script (PowerShell)
├── test_voice_router.py          # Voice intent router test suite
└── README_DEPLOY.md              # This file
```
