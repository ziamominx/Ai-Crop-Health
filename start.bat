@echo off
rem Agricure launcher — starts FastAPI backend (:8000) + Vite dev server (:5173)
start "Agricure API" /min cmd /c "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
start "Agricure Web" /min cmd /c "cd /d %~dp0frontend && npm run dev"
echo Agricure starting:
echo   Web  http://localhost:5173
echo   API  http://localhost:8000/docs
