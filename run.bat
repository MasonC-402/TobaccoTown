@echo off
rem ****************************
rem *** AUTHOR/MAINTAINER ***
rem    MASON CLEMONS | 2026
rem
rem *** ABOUT ***
rem Windows equivalent of run.sh — exports CigarScanner humidor data
rem using the uv-managed Python environment.
rem
rem Run with:  run.bat          (normal)
rem            run.bat --reset  (wipe saved login profile and re-authenticate)
rem ****************************

setlocal enabledelayedexpansion
cd /d "%~dp0"

set SCRIPT=main.py
set RESET=0

if "%~1"=="--reset" set RESET=1

where uv >nul 2>&1
if errorlevel 1 (
    echo uv is not installed. Install it from https://docs.astral.sh/uv/
    echo   e.g.  winget install astral-sh.uv
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo Error: %SCRIPT% not found in the current directory.
    pause
    exit /b 1
)

uv run python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo Installing playwright package...
    uv add playwright
)

echo Ensuring Chromium browser is installed...
uv run playwright install chromium

if "%RESET%"=="1" (
    if exist ".cs_profile" (
        echo Reset requested: deleting .cs_profile ^(you'll log in again^)...
        rmdir /s /q .cs_profile
    )
)

echo RUNNING CIGARSCANNER.COM HUMIDOR EXPORT...
uv run %SCRIPT% export --dump-json
if errorlevel 1 (
    echo Error: %SCRIPT% failed to run.
    pause
    exit /b 1
)

echo Done.
pause
