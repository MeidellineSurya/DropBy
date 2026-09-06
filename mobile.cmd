@echo off
setlocal
cd /d "%~dp0"

echo Opening the DropBy browser frontend...
start "" "%~dp0apps\api\demo\mobile.html"
