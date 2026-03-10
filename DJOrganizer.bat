@echo off
title DJOrganizer — Music Library Sorter
cls
echo.
echo   ======================================================
echo     DJOrganizer — Auto-Sort Your Music Library by Genre
echo     https://github.com/lionmit/djorganizer
echo   ======================================================
echo.

:: Check for Python
where python >nul 2>nul
if %errorlevel% equ 0 (
    python sort_main_crate.py
) else (
    where python3 >nul 2>nul
    if %errorlevel% equ 0 (
        python3 sort_main_crate.py
    ) else (
        echo   Python 3 is required but not installed.
        echo.
        echo   To install:
        echo     1. Go to https://python.org/downloads
        echo     2. Download Python 3
        echo     3. IMPORTANT: Check "Add Python to PATH" during install
        echo     4. Double-click this file again
        echo.
    )
)

echo.
echo   ------------------------------------------------------
echo   Done. You can close this window.
echo   ------------------------------------------------------
echo.
pause
