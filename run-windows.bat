@echo off
title Visibility Check Tracker - Native Runner
echo ==============================================================================
echo   STARTING VISIBILITY CHECK TRACKER (WINDOWS)
echo ==============================================================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not detected!
    echo Please run setup-windows.bat first to install all requirements.
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [*] Starting web server at http://127.0.0.1:8000 ...
echo [*] Login Credentials:
echo     Username: admin
echo     Password: tracker@2026
echo.
echo Press Ctrl+C in this terminal window to stop the server anytime.
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo [ERROR] Server exited unexpectedly.
    pause
)
