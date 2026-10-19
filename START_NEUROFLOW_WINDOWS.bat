@echo off
setlocal
cd /d "%~dp0"
echo Starting NeuroFlow Connect at http://127.0.0.1:8000
echo Synthetic data only. Press Ctrl+C to stop.
py -3 run.py
if errorlevel 1 (
  echo.
  echo Python 3.11 or newer is required. Try: python run.py
  pause
)

