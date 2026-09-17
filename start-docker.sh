#!/usr/bin/env bash
set -e

echo "=============================================================================="
echo "  VISIBILITY CHECK TRACKER - DOCKER LAUNCHER"
echo "=============================================================================="
echo ""

# 1. Check Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not in PATH."
    echo "Please install Docker from https://www.docker.com/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "[ERROR] Docker daemon is not running. Please start Docker and try again."
    exit 1
fi

# 2. Check .env
if [ ! -f ".env" ]; then
    echo "[*] Creating .env file from .env.example..."
    cp ".env.example" ".env"
    echo ""
    echo "----------------------------------------------------------------------"
    echo "[TIP] To enable remote access from your tablet or laptop,"
    echo "      you will need a free ngrok authtoken."
    echo "      Get your free token in 1 min at: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "----------------------------------------------------------------------"
    read -r -p "Enter your ngrok authtoken (or press Enter to skip for local-only): " USER_TOKEN
    if [ -n "$USER_TOKEN" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/NGROK_AUTHTOKEN=.*/NGROK_AUTHTOKEN=$USER_TOKEN/" .env
        else
            sed -i "s/NGROK_AUTHTOKEN=.*/NGROK_AUTHTOKEN=$USER_TOKEN/" .env
        fi
        echo "[*] Saved ngrok authtoken to .env"
    fi
    echo ""
fi

# 3. Launch Docker Compose
echo "[*] Starting Visibility Check Tracker & Ngrok Tunnel..."
echo "[*] (The public remote access URL will appear below once ready)"
echo ""
docker compose up --build
