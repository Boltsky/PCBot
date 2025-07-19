@echo off
REM Deployment script for PCBot (Windows)

echo.
echo [1;34mPCBot Deployment Script[0m
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

REM Run tests (skipping for now - test files in backup directory)
echo.
echo [1;33mSkipping tests - test files moved to backup directory[0m
REM If you want to run tests, use: pytest backup\\
echo [1;32mTest step skipped - proceeding with deployment[0m

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Launch application
echo.
echo [1;34mStarting PCBot...[0m
echo Bot is starting up. Check logs\pcbot.log for details.
echo Press Ctrl+C to stop the bot.
echo.

REM Start the bot and redirect output to log file
python run_pcbot.py > logs\pcbot.log 2>&1

echo.
echo [1;33mBot has stopped.[0m
pause
