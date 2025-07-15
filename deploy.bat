@echo off
REM Deployment script for PCRst Bot (Windows)

echo.
echo [1;34mPCRst Bot Deployment Script[0m
echo =====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [1;31mError: Python is not installed or not in PATH[0m
    pause
    exit /b 1
)

REM Update repository (if using git)
echo [1;34mUpdating source repository...[0m
git pull origin main 2>nul
if %errorlevel% neq 0 (
    echo [1;33mWarning: Git repository update failed or not a git repository[0m
)

REM Install/update dependencies
echo.
echo [1;34mInstalling/updating dependencies...[0m
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [1;31mError: Failed to install dependencies[0m
    pause
    exit /b 1
)

REM Run tests
echo.
echo [1;34mRunning tests...[0m
python test_focused.py
if %errorlevel% neq 0 (
    echo [1;31mTests failed. Aborting deployment.[0m
    pause
    exit /b 1
)

echo.
echo [1;32mAll tests passed successfully![0m

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Launch application
echo.
echo [1;34mStarting PCRst bot...[0m
echo Bot is starting up. Check logs\pcrst.log for details.
echo Press Ctrl+C to stop the bot.
echo.

REM Start the bot and redirect output to log file
python PCRst.py 2>&1 | tee logs\pcrst.log

echo.
echo [1;33mBot has stopped.[0m
pause
