@echo off
setlocal EnableExtensions EnableDelayedExpansion
title PCBot Deployment

echo.
echo =====================================
echo    PCBot Deployment Script
echo =====================================
echo.

REM Move to the folder where this BAT file lives
cd /d "%~dp0" || (
    echo [ERROR] Failed to change directory to script folder.
    pause
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Create logs folder
if not exist "logs" mkdir logs

REM If config.json is missing, run first-time setup
if not exist "config.json" (
    echo [INFO] No config.json found.
    echo [INFO] First-time setup will prompt for Telegram bot credentials.
    echo.
    python run_pcbot.py
    if errorlevel 1 (
        echo.
        echo [ERROR] First-time setup failed.
        pause
        exit /b 1
    )
    echo.
    echo [INFO] Setup completed successfully.
    pause
    exit /b 0
)

REM Launch bot and keep output visible in a log
echo [INFO] config.json found.
echo [INFO] Starting PCBot...
echo [INFO] Check logs\pcbot.log for details.
echo.

python run_pcbot.py > "logs\pcbot.log" 2>&1

echo.
echo [INFO] Bot has stopped.
pause
