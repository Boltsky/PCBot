@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: PCBot Prerequisites Installer
:: Installs: Chocolatey, Git, Python
:: Run this file as Administrator on a fresh Windows machine
:: ============================================================

title PCBot Prerequisites Installer
color 0A

echo.
echo  ============================================================
echo   PCBot Prerequisites Installer
echo   Chocolatey ^| Git ^| Python
echo  ============================================================
echo.

:: -----------------------------------------------------------
:: STEP 0 - Check for Administrator privileges
:: -----------------------------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] This script must be run as Administrator.
    echo  Right-click the file and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)
echo  [OK] Running as Administrator.
echo.

:: -----------------------------------------------------------
:: STEP 1 - Install Chocolatey
:: -----------------------------------------------------------
echo  [1/3] Installing Chocolatey...
echo.

:: Check if Chocolatey is already installed
where choco >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SKIP] Chocolatey is already installed.
    choco --version
) else (
    echo  Downloading and installing Chocolatey via PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    if !errorlevel! neq 0 (
        echo  [ERROR] Chocolatey installation failed. Check your internet connection.
        pause
        exit /b 1
    )
    echo  [OK] Chocolatey installed successfully.
)
echo.

:: Refresh environment so choco command is available in this session
call RefreshEnv.cmd >nul 2>&1
set "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

:: -----------------------------------------------------------
:: STEP 2 - Install Git
:: -----------------------------------------------------------
echo  [2/3] Installing Git...
echo.

where git >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SKIP] Git is already installed.
    git --version
) else (
    choco install git -y --no-progress
    if !errorlevel! neq 0 (
        echo  [ERROR] Git installation failed.
        pause
        exit /b 1
    )
    echo  [OK] Git installed successfully.
)
echo.

:: -----------------------------------------------------------
:: STEP 3 - Install Python
:: -----------------------------------------------------------
echo  [3/3] Installing Python...
echo.

where python >nul 2>&1
if %errorlevel% equ 0 (
    echo  [SKIP] Python is already installed.
    python --version
) else (
    choco install python -y --no-progress
    if !errorlevel! neq 0 (
        echo  [ERROR] Python installation failed.
        pause
        exit /b 1
    )
    echo  [OK] Python installed successfully.
)
echo.

:: -----------------------------------------------------------
:: STEP 4 - Refresh PATH and verify all installs
:: -----------------------------------------------------------
echo  Refreshing environment variables...
call RefreshEnv.cmd >nul 2>&1

:: Manually refresh PATH from registry in case RefreshEnv is unavailable
for /f "skip=2 tokens=3*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%a %%b"
for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USR_PATH=%%a %%b"
set "PATH=%SYS_PATH%;%USR_PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

echo.
echo  ============================================================
echo   Installation Summary
echo  ============================================================

:: Verify Chocolatey
where choco >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('choco --version 2^>nul') do echo  [OK] Chocolatey : %%v
) else (
    echo  [WARN] Chocolatey not found in PATH - may need to restart cmd
)

:: Verify Git
where git >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('git --version 2^>nul') do echo  [OK] %%v
) else (
    echo  [WARN] Git not found in PATH - may need to restart cmd
)

:: Verify Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('python --version 2^>nul') do echo  [OK] %%v
) else (
    echo  [WARN] Python not found in PATH - may need to restart cmd
)

echo  ============================================================
echo.
echo  All prerequisites installed! You may need to open a new
echo  Command Prompt window for PATH changes to take full effect.
echo.
pause
exit /b 0
