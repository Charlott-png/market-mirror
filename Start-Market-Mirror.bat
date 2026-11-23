@echo off
setlocal
title Market Mirror Server

REM Switch to the folder containing this BAT file.
cd /d "%~dp0"

REM Check that the startup script exists.
if not exist ".\scripts\local.ps1" (
    echo ERROR: Cannot find scripts\local.ps1.
    echo Save this BAT file inside the market-mirror folder.
    pause
    exit /b 1
)

echo Starting Market Mirror...
echo Once started, open http://127.0.0.1:5000
echo Keep this window open while using the app.
echo.

REM Bypass execution policy only for this PowerShell session.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File ".\scripts\local.ps1" serve

REM Keep the window open after the server exits.
echo.
echo The server has stopped. Any error messages appear above.
pause