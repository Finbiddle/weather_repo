#!/bin/bash
set -e

PROJECT_DIR="/home/ubuntu/cron"
VENV_DIR="$PROJECT_DIR/venv"
SCRIPT="$PROJECT_DIR/fetch_weather.py"

cd "$PROJECT_DIR" || exit 1

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source "$VENV_DIR/bin/activate"
fi

python "$SCRIPT"
