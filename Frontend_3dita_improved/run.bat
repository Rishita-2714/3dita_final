@echo off
REM Start the backend and frontend in separate windows for easy development.

cd /d "%~dp0backend"
start "3DITA Backend" cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8010"

cd /d "%~dp0frontend"
start "3DITA Frontend" cmd /k "npm run dev"

echo Started backend and frontend in separate windows.
