@echo off
REM MandiSense AI - Agent Runner Batch File
REM Usage: run_agents.bat [commodity] [mandi]
REM Example: run_agents.bat tomato kolar

setlocal enabledelayedexpansion

set "COMMODITY=%1"
set "MANDI=%2"

if "!COMMODITY!"=="" set "COMMODITY=tomato"
if "!MANDI!"=="" set "MANDI=kolar"

echo.
echo ============================================================
echo MandiSense AI - Agent Execution
echo ============================================================
echo Commodity: !COMMODITY!
echo Mandi: !MANDI!
echo ============================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment not found
    exit /b 1
)

".venv\Scripts\python.exe" "run_agents.py" "!COMMODITY!" "!MANDI!"

pause
