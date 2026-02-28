#!/bin/bash
set -e

WORKSPACE_DIR="/home/jason/.openclaw/workspace/star-office-ui"
cd "$WORKSPACE_DIR"

if pgrep -f "backend/app.py" > /dev/null; then
    echo "Star Office UI backend is already running."
else
    echo "Starting Star Office UI backend..."
    nohup python3 backend/app.py > backend.log 2>&1 &
    echo "Started backend with PID $!"
fi

if pgrep -f "office_sync.py" > /dev/null; then
    echo "Star Office UI sync daemon is already running."
else
    echo "Starting Star Office UI sync daemon..."
    chmod +x office_sync.py
    nohup ./office_sync.py > sync.log 2>&1 &
    echo "Started sync daemon with PID $!"
fi
