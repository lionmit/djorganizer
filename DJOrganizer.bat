@echo off
title DJOrganizer
cd /d "%~dp0"

echo.
echo   DJOrganizer - starting up
echo.

:: ---- Python check -------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo   Python 3 is required and was not found.
    echo.
    echo   1. Go to https://www.python.org/downloads/
    echo   2. Download Python 3
    echo   3. IMPORTANT: tick "Add Python to PATH" during install
    echo   4. Double-click this file again
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do echo   Found %%i

:: ---- Virtual environment, first run only --------------------------
if not exist ".venv" (
    echo   Setting up, first run only. This takes a minute.
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo   Could not create the environment.
        echo   Try running this file again, or reinstall Python with
        echo   "Add Python to PATH" ticked.
        echo.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

:: ---- Dependencies -------------------------------------------------
echo   Checking dependencies
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo   Could not install dependencies. Check your internet connection
    echo   and run this file again.
    echo.
    pause
    exit /b 1
)

:: ---- Launch -------------------------------------------------------
:: app.py picks its own free port and opens the browser itself.
:: Do not start it twice and do not open a browser here: doing so used to
:: leave two servers running, three browser tabs, and the folder picker
:: appearing twice.
echo.
echo   Launching. Your browser will open on its own.
echo   Keep this window open while you work. Close it to stop.
echo.

python app.py

echo.
echo   DJOrganizer stopped.
pause
