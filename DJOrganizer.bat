@echo off
title DJOrganizer v19
cd /d "%~dp0"

echo DJOrganizer v19 — Starting...
echo.

:: Check Python 3
python --version >nul 2>&1
if errorlevel 1 (
    echo Python 3 is required but not installed.
    echo Download it from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do echo Found: %%i

:: Create venv if needed
if not exist ".venv" (
    echo Setting up environment ^(first run only^)...
    python -m venv .venv
)

:: Activate venv
call .venv\Scripts\activate

:: Install dependencies
echo Checking dependencies...
pip install -r requirements.txt --quiet 2>nul

echo.
echo Launching DJOrganizer...
echo Close this window to stop the server.
echo.

:: Start Flask and capture port from stdout
:: Write server output to a temp file so we can parse the port
set "PORTFILE=%TEMP%\djorganizer_port.txt"
start /b cmd /c "python app.py > "%PORTFILE%" 2>&1"

:: Wait for server to start and extract port
set PORT=5555
for /l %%i in (1,1,10) do (
    timeout /t 1 >nul
    if exist "%PORTFILE%" (
        for /f "tokens=*" %%a in ('findstr /c:"127.0.0.1:" "%PORTFILE%"') do (
            for /f "tokens=2 delims=:" %%b in ("%%a") do set PORT=%%b
        )
    )
    if not "!PORT!"=="5555" goto :open_browser
)

:open_browser
start http://127.0.0.1:%PORT%

:: Run Flask in foreground (restart so it's the main process)
python app.py

echo.
echo DJOrganizer stopped.
pause
