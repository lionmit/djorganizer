#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  DJOrganizer — Double-click to run
#  Auto-sorts your DJ music library into genre folders.
#  https://github.com/lionmit/djorganizer
# ═══════════════════════════════════════════════════════════

# Move to the folder this script lives in
cd "$(dirname "$0")"

clear
echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║         DJOrganizer — Music Library Sorter       ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""

# Check for Python 3
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    # Check if 'python' is actually Python 3
    PY_VERSION=$(python --version 2>&1 | grep -oE '[0-9]+' | head -1)
    if [ "$PY_VERSION" = "3" ]; then
        PYTHON=python
    else
        echo "  Python 3 is required but not installed."
        echo ""
        echo "  To install:"
        echo "    1. Go to https://python.org/downloads"
        echo "    2. Download Python 3"
        echo "    3. Install it"
        echo "    4. Double-click this file again"
        echo ""
        read -p "  Press Enter to close..."
        exit 1
    fi
else
    echo "  Python 3 is required but not installed."
    echo ""
    echo "  To install:"
    echo "    1. Go to https://python.org/downloads"
    echo "    2. Download Python 3"
    echo "    3. Install it"
    echo "    4. Double-click this file again"
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

# Auto-install mutagen for better track classification (one time only)
if ! $PYTHON -c "import mutagen" 2>/dev/null; then
    echo "  Setting up for first use... (one time only)"
    echo ""
    $PYTHON -m pip install --user mutagen --quiet 2>/dev/null
    if $PYTHON -c "import mutagen" 2>/dev/null; then
        echo "  ✓ Metadata reading enabled — more tracks will be classified"
    else
        echo "  (Metadata reading unavailable — tool works fine without it)"
    fi
    echo ""
fi

# Run the sorter in interactive mode
$PYTHON sort_main_crate.py

echo ""
echo "  ─────────────────────────────────────────────────"
echo "  Done. You can close this window."
echo "  ─────────────────────────────────────────────────"
echo ""
read -p "  Press Enter to close..."
