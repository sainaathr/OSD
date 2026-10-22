# OSD Cross-Platform Packaging & Distribution Guide

This document provides reproducible build and packaging instructions for **OSD (Operating System Diagnostics)** on Windows, Linux, and macOS.

---

## 1. Prerequisites

- **Python 3.10+** (Python 3.12 recommended)
- **PySide6-Essentials** & core dependencies (listed in `requirements.txt`)
- **PyInstaller 6.0+**

```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
pip install pyinstaller
```

---

## 2. Windows 10/11 Packaging

### Automated Build
Run the provided batch script:
```cmd
scripts\build_windows.bat
```

### Manual PyInstaller Command
```cmd
pyinstaller --noconfirm --clean osd.spec
```

### Output
- Directory bundle: `dist\OSD\`
- Executable: `dist\OSD\OSD.exe`

### Windows Notes & SmartScreen
- Unsigned binaries may trigger Windows SmartScreen ("Windows protected your PC").
- For production distribution, sign `dist\OSD\OSD.exe` using `signtool.exe` with a valid Sectigo/DigiCert Code Signing Certificate:
  ```cmd
  signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a dist\OSD\OSD.exe
  ```

---

## 3. Linux Distribution Packaging

### Supported Distributions
- Ubuntu 20.04, 22.04, 24.04 LTS
- Debian 11, 12
- Fedora 38, 39, 40
- Arch Linux

### System Prerequisites
PySide6 uses Qt6, which requires OpenGL and X11/Wayland dynamic libraries. Ensure they are installed:

**Debian / Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y \
    libgl1-mesa-glx \
    libegl1 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libx11-xcb1
```

**Fedora / RHEL:**
```bash
sudo dnf install -y \
    mesa-libGL \
    mesa-libEGL \
    libxkbcommon-x11 \
    dbus-libs \
    fontconfig
```

### Automated Build
```bash
chmod +x scripts/build_linux.sh
./scripts/build_linux.sh
```

### Output
- Directory bundle: `dist/OSD/`
- Executable: `dist/OSD/OSD`

---

## 4. macOS Packaging

### Supported Versions & Architectures
- macOS 12 (Monterey), 13 (Ventura), 14 (Sonoma), 15 (Sequoia)
- Apple Silicon (M1/M2/M3/M4, `arm64`) and Intel (`x86_64`)

### Automated Build
```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

### Code Signing & Apple Notarization
macOS Gatekeeper blocks unsigned third-party applications. To distribute outside the Mac App Store:

1. **Sign with Developer ID:**
   ```bash
   codesign --deep --force --verify --verbose \
     --options runtime \
     --sign "Developer ID Application: Your Company Name (TEAM_ID)" \
     dist/OSD
   ```

2. **Package into a Zip or DMG:**
   ```bash
   ditto -c -k --keepParent dist/OSD dist/OSD.zip
   ```

3. **Submit to Apple Notary Service:**
   ```bash
   xcrun notarytool submit dist/OSD.zip \
     --keychain-profile "AC_NOTARY_PROFILE" \
     --wait
   ```

4. **Staple Notarization Ticket:**
   ```bash
   xcrun stapler staple dist/OSD
   ```

---

## 5. Continuous Integration (CI)

A GitHub Actions workflow is provided at `.github/workflows/build_matrix.yml`. It automatically tests and builds OSD across:
- `windows-latest`
- `ubuntu-latest`
- `macos-latest`

Build artifacts from all three platforms are automatically bundled and stored in CI runs.
