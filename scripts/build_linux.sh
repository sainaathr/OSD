#!/usr/bin/env bash
# ==============================================================================
# OSD (Operating System Diagnostics) — Linux Distribution Build Script
# Targets: Ubuntu 20.04+, Debian 11+, Fedora 38+, Arch Linux
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "======================================================="
echo "  OSD (Operating System Diagnostics) — Linux Build"
echo "======================================================="
echo ""

# 1. Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[1/4] Found Python ${PYTHON_VERSION}"

# 2. Check essential system libraries for PySide6 GUI on Linux
echo "[2/4] Checking Linux GUI runtime dependencies..."
MISSING_LIBS=()
for lib in libGL.so.1 libxkbcommon.so.0; do
    if ! ldconfig -p 2>/dev/null | grep -q "$lib"; then
        MISSING_LIBS+=("$lib")
    fi
done

if [ ${#MISSING_LIBS[@]} -gt 0 ]; then
    echo "[WARNING] The following shared libraries might be missing for Qt6/PySide6 GUI:"
    for lib in "${MISSING_LIBS[@]}"; do
        echo "  - $lib"
    done
    echo "On Debian/Ubuntu, install with:"
    echo "  sudo apt-get install -y libgl1-mesa-glx libegl1 libxkbcommon-x11-0 libdbus-1-3"
    echo "On Fedora/RHEL, install with:"
    echo "  sudo dnf install -y mesa-libGL libxkbcommon-x11 dbus-libs"
fi

# 3. Virtual environment setup
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[3/4] Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# 4. PyInstaller build
echo "[4/4] Building standalone Linux application with PyInstaller..."
pyinstaller --noconfirm --clean osd.spec

if [ -f "dist/OSD/OSD" ]; then
    chmod +x "dist/OSD/OSD"
    echo "[SUCCESS] Standalone Linux executable built at: dist/OSD/OSD"
    ls -lh dist/OSD/OSD
else
    echo "[ERROR] Expected binary dist/OSD/OSD was not found!"
    exit 1
fi

echo ""
echo "======================================================="
echo "Build complete. Run with: ./dist/OSD/OSD"
echo "======================================================="
