@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo   OSD (Operating System Diagnostics) — Windows Build
echo =======================================================
echo.

cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    set "PYINSTALLER_EXE=.venv\Scripts\pyinstaller.exe"
) else (
    set "PYTHON_EXE=python"
    set "PYINSTALLER_EXE=pyinstaller"
)

echo [1/3] Verifying Python & PyInstaller environment...
"%PYTHON_EXE%" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python environment not found. Please setup .venv first.
    exit /b 1
)

"%PYINSTALLER_EXE%" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing pyinstaller in virtual environment...
    "%PYTHON_EXE%" -m pip install pyinstaller
)

echo [2/3] Building OSD standalone desktop application with PyInstaller...
"%PYINSTALLER_EXE%" --noconfirm --clean osd.spec
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed!
    exit /b %errorlevel%
)

echo [3/4] Validating build artifacts...
if exist "dist\OSD\OSD.exe" (
    echo [SUCCESS] Windows executable created at dist\OSD\OSD.exe
    dir "dist\OSD\OSD.exe"
) else (
    echo [ERROR] Expected binary dist\OSD\OSD.exe was not created!
    exit /b 1
)

echo [4/4] Packaging release archive (dist\OSD-windows-x64.zip)...
powershell -NoProfile -Command "if (Test-Path 'dist\OSD-windows-x64.zip') { Remove-Item 'dist\OSD-windows-x64.zip' -Force }; Compress-Archive -Path 'dist\OSD' -DestinationPath 'dist\OSD-windows-x64.zip' -Force"
if exist "dist\OSD-windows-x64.zip" (
    echo [SUCCESS] Release package created at dist\OSD-windows-x64.zip
    dir "dist\OSD-windows-x64.zip"
) else (
    echo [WARNING] Could not create dist\OSD-windows-x64.zip
)

echo.
echo =======================================================
echo Build complete.
echo Executable: dist\OSD\OSD.exe
echo Archive:    dist\OSD-windows-x64.zip
echo =======================================================

