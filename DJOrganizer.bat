@echo off
title DJOrganizer
cd /d "%~dp0"

echo.
echo   DJOrganizer - starting up
echo.

:: ---- Python check -------------------------------------------------
:: Try the py launcher first. The official python.org installer always
:: installs py.exe, and it keeps working even when "python" does not,
:: which is the usual reason Windows reports Python as missing.
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"

if not defined PY (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY=python"
)

if not defined PY (
    python3 --version >nul 2>&1
    if not errorlevel 1 set "PY=python3"
)

if not defined PY (
    echo   Python 3 was not found.
    echo.
    echo   Install it:
    echo     1. Go to https://www.python.org/downloads/
    echo     2. Download Python 3 for Windows and run the installer
    echo     3. On the FIRST screen, tick "Add python.exe to PATH" at the
    echo        bottom. This is the step everyone misses.
    echo     4. Finish, then double-click this file again.
    echo.
    echo   Already installed it and still seeing this?
    echo     Windows ships a fake python.exe that opens the Microsoft Store.
    echo     Turn it off: Settings ^> Apps ^> Advanced app settings ^>
    echo     App execution aliases ^> switch OFF python.exe and python3.exe
    echo     Then double-click this file again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PY% --version') do echo   Found %%i

:: ---- Are the other files actually here? ---------------------------
:: Double-clicking a .bat from inside a zip makes Windows extract only
:: that one file to a temp folder and run it there, so everything else
:: is missing. This is the most common first-run failure.
if not exist "requirements.txt" goto :not_extracted
if not exist "app.py" goto :not_extracted
goto :files_ok

:not_extracted
echo.
echo   The rest of DJOrganizer is missing from this folder.
echo.
echo   You are almost certainly running this from inside the ZIP.
echo   Windows only unpacks the one file you double-click.
echo.
echo   Fix it:
echo     1. Right-click the downloaded ZIP file
echo     2. Choose "Extract All"
echo     3. Open the folder it creates ^(djorganizer-main^)
echo     4. Double-click DJOrganizer.bat in THERE
echo.
echo   Current folder: %CD%
echo.
pause
exit /b 1

:files_ok

:: ---- Virtual environment, first run only --------------------------
if not exist ".venv" (
    echo   Setting up, first run only. This takes a minute.
    %PY% -m venv .venv
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
    echo   Could not install dependencies. Check your internet connection,
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

%PY% app.py

echo.
echo   DJOrganizer stopped.
pause
