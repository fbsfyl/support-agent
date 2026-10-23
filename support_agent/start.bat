@echo off
title Support Agent - Launcher
cd /d "%~dp0"

echo ============================================
echo    Support Agent - Smart Ticketing System
echo ============================================
echo.

REM If port 5000 is already listening, just open the browser.
netstat -aon | findstr ":5000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] Service already running, opening browser...
    start "" http://localhost:5000
    goto :end
)

echo [1/2] Starting backend service at http://localhost:5000 ...
start "SupportAgent-Server" cmd /k "python app.py"

echo [2/2] Waiting for the service, then opening browser...
timeout /t 3 /nobreak >nul
start "" http://localhost:5000

echo.
echo Done! The browser has been opened.
echo To stop the service, double-click stop.bat
echo.

:end
pause
