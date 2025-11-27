@echo off
title WriterAI Launcher

echo 🚀 Starting WriterAI...

:: Check for virtual environment
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate

:: Install dependencies if needed
if not exist "venv\.installed" (
    echo ⬇️ Installing dependencies...
    pip install -r requirements.txt
    type nul > venv\.installed
)

:: Start the application
echo ✨ Launching Web Server & Real-Time Engine...
echo 🌐 Dashboard: http://localhost:8080
set PYTHONPATH=%PYTHONPATH%;%CD%\prometheus_novel
python -m prometheus_novel.interfaces.web.app

pause
