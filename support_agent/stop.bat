@echo off
title Support Agent - Stop
cd /d "%~dp0"

echo ============================================
echo    Support Agent - Smart Ticketing System
echo ============================================
echo.

set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    echo Stopping service process PID=%%a ...
    taskkill /f /pid %%a >nul 2>&1
    set "FOUND=1"
)

if "%FOUND%"=="1" (
    echo.
    echo [DONE] Service stopped.
) else (
    echo.
    echo [INFO] No running service found on port 5000.
)

echo.
pause
