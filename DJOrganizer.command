#!/bin/bash
# DJOrganizer v19 — Double-click to launch
# Automatically sets up Python environment and opens the app

cd "$(dirname "$0")"

echo "🎵 DJOrganizer v19 — Starting..."
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "   Download it from: https://www.python.org/downloads/"
    echo ""
    echo "Press Enter to close..."
    read
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "📦 Setting up environment (first run only)..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "📦 Checking dependencies..."
pip install -r requirements.txt --quiet 2>/dev/null

echo ""
echo "🚀 Launching DJOrganizer..."
echo "   Close this window to stop the server."
echo ""

# Start Flask in background, capture output to detect actual port
python app.py 2>&1 &
SERVER_PID=$!

# Wait for server to print its port, then open browser
for i in $(seq 1 20); do
    sleep 0.5
    # Check if server printed its URL
    PORT=$(lsof -iTCP -sTCP:LISTEN -nP -p $SERVER_PID 2>/dev/null | grep -oE '127\.0\.0\.1:[0-9]+' | head -1 | cut -d: -f2)
    if [ -n "$PORT" ]; then
        echo "   Opening http://127.0.0.1:$PORT"
        open "http://127.0.0.1:$PORT"
        break
    fi
done

# Wait for server process — closing Terminal kills it
wait $SERVER_PID

echo ""
echo "DJOrganizer stopped."
