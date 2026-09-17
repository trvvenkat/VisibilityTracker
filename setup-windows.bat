@echo off
title Visibility Check Tracker - Windows Setup
echo ==============================================================================
echo   VISIBILITY CHECK TRACKER - NATIVE WINDOWS SETUP
echo ==============================================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in your PATH!
    echo Please install Python 3.11+ from https://www.python.org/
    echo Make sure to check the box "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [*] Python found:
python --version

:: 2. Create Virtual Environment if not exists
if not exist ".venv" (
    echo [*] Creating virtual environment in .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Install Requirements
echo [*] Installing required Python dependencies...
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)

:: 4. Install Playwright Chromium
echo [*] Installing Playwright Chromium browser binary...
playwright install chromium
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright browser.
    pause
    exit /b 1
)

:: 5. Create .env if not exists
if not exist ".env" (
    echo [*] Creating .env from .env.example...
    copy ".env.example" ".env" >nul
)

echo.
echo ==============================================================================
echo [SUCCESS] Setup complete! You can now launch the tracker by running:
echo           run-windows.bat
echo ==============================================================================
echo.
pause
