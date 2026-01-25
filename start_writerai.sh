#!/bin/bash

# WriterAI Launcher - Unix/Linux/macOS

set -e

echo ""
echo "██     ██ ██████  ██ ████████ ███████ ██████   █████  ██"
echo "██     ██ ██   ██ ██    ██    ██      ██   ██ ██   ██ ██"
echo "██  █  ██ ██████  ██    ██    █████   ██████  ███████ ██"
echo "██ ███ ██ ██   ██ ██    ██    ██      ██   ██ ██   ██ ██"
echo " ███ ███  ██   ██ ██    ██    ███████ ██   ██ ██   ██ ██"
echo ""
echo "AI-Powered Novel Generation System"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies if needed
if [ ! -f "venv/.deps_installed" ]; then
    echo "[SETUP] Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch venv/.deps_installed
else
    echo "[INFO] Dependencies already installed"
fi

# Create necessary directories
mkdir -p prometheus_novel/data/projects
mkdir -p prometheus_novel/logs

# Set PYTHONPATH
export PYTHONPATH="$(pwd):$(pwd)/prometheus_novel:$PYTHONPATH"

echo ""
echo "[INFO] Starting WriterAI Web Dashboard..."
echo "[INFO] Dashboard: http://localhost:8080"
echo "[INFO] API Docs:  http://localhost:8080/docs"
echo "[INFO] Press Ctrl+C to stop"
echo ""

# Start the application
python3 -m prometheus_novel.interfaces.web.app --host 0.0.0.0 --port 8080

# Deactivate on exit
deactivate 2>/dev/null || true
