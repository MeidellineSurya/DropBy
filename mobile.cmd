@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0apps\mobile"

where node >nul 2>&1
if errorlevel 1 (
    echo Node.js is not installed or is not available in PATH.
    echo Install the current Node.js LTS release, then run mobile.cmd again.
    exit /b 1
)

if not exist ".env" (
    set "LAN_IP="
    for /f "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /R /C:"IPv4.*192\.168\."') do if not defined LAN_IP set "LAN_IP=%%I"
    if not defined LAN_IP for /f "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /C:"IPv4 Address"') do if not defined LAN_IP set "LAN_IP=%%I"
    set "LAN_IP=!LAN_IP: =!"
    if not defined LAN_IP set "LAN_IP=127.0.0.1"
    echo EXPO_PUBLIC_API_URL=http://!LAN_IP!:8000> .env
    echo Created apps\mobile\.env using this computer's address: !LAN_IP!
)

if not exist "node_modules" (
    echo Installing the mobile dependencies...
    set "NODE_OPTIONS=--use-system-ca"
    call npm.cmd install
    if errorlevel 1 exit /b 1
)

echo.
echo Starting DropBy for Expo Go...
echo Keep this window open and scan the QR code with your phone.
echo The backend must also be running with dev.cmd.
echo.
call npm.cmd start -- --lan
exit /b %errorlevel%
