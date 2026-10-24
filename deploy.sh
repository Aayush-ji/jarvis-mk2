#!/usr/bin/env bash
# =============================================================================
# J.A.R.V.I.S. Mk.II — One-Command Server Deployment (Linux/macOS/WSL)
# =============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "[JARVIS] Beginning deployment..."

# 1. Prerequisites
command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "pip3 not found"; exit 1; }

# 2. Environment
if [[ ! -f .env ]]; then
  echo "[JARVIS] .env not found. Copying from .env.example..."
  cp .env.example .env
  echo "[JARVIS] Please edit .env with your domain and secrets, then re-run this script."
  exit 0
fi

# Auto-generate secret if placeholder remains
if grep -q "replace-with-a-64-character" .env 2>/dev/null; then
  SECRET=$(openssl rand -hex 32)
  sed -i "s/replace-with-a-64-character-hex-secret-string/$SECRET/" .env
  echo "[JARVIS] Generated JARVIS_SECRET automatically."
fi

# 3. Python environment
python3 -m venv venv || true
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Database initialization
python -c "from server import init_db; init_db()" || echo "[JARVIS] DB init skipped (server handles it on start)."

# 5. Choose deployment mode
echo ""
echo "Select deployment mode:"
echo "  1) Docker Compose (recommended for production)"
echo "  2) Direct systemd service"
read -rp "Choice [1]: " DEPLOY_MODE
DEPLOY_MODE=${DEPLOY_MODE:-1}

if [[ "$DEPLOY_MODE" == "1" ]]; then
  echo "[JARVIS] Starting with Docker Compose..."
  command -v docker >/dev/null 2>&1 || { echo "Docker not found"; exit 1; }
  command -v docker-compose >/dev/null 2>&1 || { echo "docker-compose not found"; exit 1; }
  docker-compose up -d --build
  echo "[JARVIS] Relay is live at https://$DOMAIN (or http://localhost:8765 locally)"
else
  echo "[JARVIS] Installing systemd service..."
  sudo cp systemd/jarvis.service /etc/systemd/system/jarvis.service
  sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|" /etc/systemd/system/jarvis.service
  sudo sed -i "s|EnvironmentFile=.*|EnvironmentFile=$PROJECT_DIR/.env|" /etc/systemd/system/jarvis.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now jarvis
  echo "[JARVIS] Service started. Check status: sudo systemctl status jarvis"
fi

echo ""
echo "[JARVIS] Deployment complete."
echo "  - Admin dashboard: https://$DOMAIN/dashboard"
echo "  - API base:        https://$DOMAIN"
echo "  - WebSocket:       wss://$DOMAIN/ws/{device_id}"
