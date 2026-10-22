@echo off
setlocal enabledelayedexpansion

title OSD — Operating System Diagnostics ^& Recovery Assistant
echo =====================================================================
echo   OSD — Operating System Diagnostics ^& Recovery Assistant
echo =====================================================================
echo.

:: Change to current directory
cd /d "%~dp0"

:: 1. Locate suitable Python interpreter
set "PY_CMD="

py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py -3.12"
    goto :found_python
)

py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py -3"
    goto :found_python
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :found_python
)

echo [ERROR] Python 3.11+ is required but was not found on your system.
echo Please install Python 3.11 or newer from https://www.python.org/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:found_python
echo [1/3] Using Python: %PY_CMD%

:: 2. Check or create virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [2/3] Creating virtual environment in .venv ...
    %PY_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Installing dependencies from requirements.txt ...
    .\.venv\Scripts\pip.exe install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install requirements.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Virtual environment .venv detected.
)

:: 3. Launch OSD
echo [3/3] Launching OSD desktop application...
echo.
.\.venv\Scripts\python.exe main.py

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] OSD exited with code %errorlevel%.
    pause
)
