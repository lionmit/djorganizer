@echo off
title DJOrganizer — Music Library Sorter
cls
echo.
echo   ======================================================
echo     DJOrganizer — Auto-Sort Your Music Library by Genre
echo     https://github.com/lionmit/djorganizer
echo   ======================================================
echo.

:: Find Python
set PYTHON=
where python >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON=python
) else (
    where python3 >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON=python3
    ) else (
        echo   Python 3 is required but not installed.
        echo.
        echo   To install:
        echo     1. Go to https://python.org/downloads
        echo     2. Download Python 3
        echo     3. IMPORTANT: Check "Add Python to PATH" during install
        echo     4. Double-click this file again
        echo.
        goto :done
    )
)

:: Auto-install mutagen for better track classification (one time only)
%PYTHON% -c "import mutagen" >nul 2>nul
if %errorlevel% neq 0 (
    echo   Setting up for first use... (one time only)
    echo.
    %PYTHON% -m pip install --user mutagen --quiet >nul 2>nul
    %PYTHON% -c "import mutagen" >nul 2>nul
    if %errorlevel% equ 0 (
        echo   Metadata reading enabled — more tracks will be classified
    ) else (
        echo   (Metadata reading unavailable — tool works fine without it)
    )
    echo.
)

:: Run the sorter
%PYTHON% sort_main_crate.py

:done

echo.
echo   ------------------------------------------------------
echo   Done. You can close this window.
echo   ------------------------------------------------------
echo.
pause
