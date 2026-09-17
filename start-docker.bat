@echo off
setlocal enabledelayedexpansion
title Visibility Check Tracker Launcher

echo ==============================================================================
echo   VISIBILITY CHECK TRACKER - DOCKER LAUNCHER
echo ==============================================================================
echo.

:: 1. Check if Docker is installed and running
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker was not found on your system!
    echo Please install Docker Desktop for Windows from:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is installed but does not appear to be running.
    echo Please launch Docker Desktop and wait until the whale icon shows "Engine running",
    echo then run this script again.
    echo.
    pause
    exit /b 1
)

:: 2. Check for .env file
if not exist ".env" (
    echo [*] Creating .env file from .env.example...
    copy ".env.example" ".env" >nul
    echo.
    echo ----------------------------------------------------------------------
    echo [TIP] To enable remote access from your tablet or laptop,
    echo       you will need a free ngrok authtoken.
    echo       Get your free token in 1 min at: https://dashboard.ngrok.com/get-started/your-authtoken
    echo ----------------------------------------------------------------------
    set /p USER_TOKEN="Enter your ngrok authtoken (or press Enter to skip for local-only): "
    if not "!USER_TOKEN!"=="" (
        powershell -Command "(Get-Content .env) -replace 'NGROK_AUTHTOKEN=', 'NGROK_AUTHTOKEN=!USER_TOKEN!' | Set-Content .env"
        echo [*] Saved ngrok authtoken to .env
    )
    echo.
)

:: 3. Launch Docker Compose
echo [*] Starting Visibility Check Tracker & Ngrok Tunnel...
echo [*] (The public remote access URL will appear below once ready)
echo.
docker compose up --build

if errorlevel 1 (
    echo.
    echo [ERROR] Docker Compose encountered an error.
    pause
)
