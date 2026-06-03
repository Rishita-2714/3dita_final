@echo off
REM Start the backend and frontend in separate windows for stable demo mode.

cd /d "%~dp0backend"
start "3DITA Backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8010"

cd /d "%~dp0frontend"
start "3DITA Frontend" cmd /k "npm run dev"

echo Started backend and frontend in separate windows.
