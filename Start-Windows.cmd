@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title VRC Chatbox 1.4

echo =====================================================
echo   VRC Chatbox - VRChat Companion v1.4
echo =====================================================
echo.
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 (
    echo [ERROR] Cannot create environment. Install Python 3.10+ with PATH enabled.
    pause
    exit /b 1
  )
)
echo [2/3] Installing/updating dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Dependencies failed. See the error above.
  pause
  exit /b 1
)
echo [3/3] Starting VRC Chatbox...
echo.
echo.
echo VRChat OSC must be enabled. Press CTRL+C to stop.
echo.
".venv\Scripts\python.exe" "HTML osc chat\osc_viewer.py"
echo.
echo Server stopped.
pause
