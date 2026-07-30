#!/bin/bash
# DJOrganizer — double-click to launch.
# Sets up the Python environment on first run, then starts the app.

cd "$(dirname "$0")"

echo ""
echo "  DJOrganizer - starting up"
echo ""

# ---- Python check ---------------------------------------------------
if ! command -v python3 &> /dev/null; then
    echo "  Python 3 is required and was not found."
    echo ""
    echo "  1. Go to https://www.python.org/downloads/"
    echo "  2. Download and install Python 3"
    echo "  3. Double-click this file again"
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

echo "  Found $(python3 --version)"

# ---- Virtual environment, first run only ----------------------------
if [ ! -d ".venv" ]; then
    echo "  Setting up, first run only. This takes a minute."
    if ! python3 -m venv .venv; then
        echo ""
        echo "  Could not create the environment. Try again, or reinstall Python 3."
        echo ""
        read -p "  Press Enter to close..."
        exit 1
    fi
fi

source .venv/bin/activate

# ---- Dependencies ---------------------------------------------------
echo "  Checking dependencies"
if ! pip install -r requirements.txt --quiet --disable-pip-version-check; then
    echo ""
    echo "  Could not install dependencies. Check your internet connection and try again."
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

# ---- Launch ---------------------------------------------------------
# app.py picks its own free port and opens the browser itself.
# Do not start it twice and do not open a browser here, or you get
# duplicate tabs and a second folder picker.
echo ""
echo "  Launching. Your browser will open on its own."
echo "  Keep this window open while you work. Close it to stop."
echo ""

python app.py

echo ""
echo "  DJOrganizer stopped."
read -p "  Press Enter to close..."
