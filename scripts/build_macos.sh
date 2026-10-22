#!/usr/bin/env bash
# ==============================================================================
# OSD (Operating System Diagnostics) — macOS Build & Packaging Script
# Targets: macOS 12 (Monterey), 13 (Ventura), 14 (Sonoma), 15 (Sequoia)
# Architecture: Apple Silicon (arm64) and Intel (x86_64)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "======================================================="
echo "  OSD (Operating System Diagnostics) — macOS Build"
echo "======================================================="
echo ""

# 1. Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is required. Install via Homebrew or python.org."
    exit 1
fi

echo "[1/4] Checking macOS build tools..."
if ! command -v codesign &> /dev/null; then
    echo "[WARNING] Xcode command line tools not found. Run 'xcode-select --install'."
fi

# 2. Virtual environment setup
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[2/4] Setting up Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# 3. PyInstaller macOS build
echo "[3/4] Building macOS executable..."
pyinstaller --noconfirm --clean osd.spec

# 4. Ad-hoc signing for local development or check production signing identity
echo "[4/4] Applying code signature..."
if [ -d "dist/OSD" ]; then
    echo "Applying ad-hoc signature to satisfy Gatekeeper locally:"
    codesign --force --deep --sign - "dist/OSD"
    echo "[SUCCESS] macOS build completed at: dist/OSD"
else
    echo "[ERROR] dist/OSD was not created."
    exit 1
fi

echo ""
echo "======================================================="
echo "macOS Distribution Notes:"
echo "1. To create a notarized .app or .dmg for distribution, sign with your Apple Developer ID:"
echo "   codesign --deep --force --options runtime --sign \"Developer ID Application: Your Name (TeamID)\" dist/OSD"
echo "2. Submit for Apple notarization:"
echo "   xcrun notarytool submit dist/OSD.zip --keychain-profile \"AC_PASSWORD\" --wait"
echo "3. Staple ticket:"
echo "   xcrun stapler staple dist/OSD.app"
echo "======================================================="
