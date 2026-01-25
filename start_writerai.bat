@echo off
title WriterAI Launcher
setlocal enabledelayedexpansion

echo.
echo  ██     ██ ██████  ██ ████████ ███████ ██████   █████  ██
echo  ██     ██ ██   ██ ██    ██    ██      ██   ██ ██   ██ ██
echo  ██  █  ██ ██████  ██    ██    █████   ██████  ███████ ██
echo  ██ ███ ██ ██   ██ ██    ██    ██      ██   ██ ██   ██ ██
echo   ███ ███  ██   ██ ██    ██    ███████ ██   ██ ██   ██ ██
echo.
echo  AI-Powered Novel Generation System
echo.

:: Change to script directory
cd /d "%~dp0"

:: Check Python installation
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check for virtual environment
if not exist "venv" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

:: Install/update dependencies if needed
if not exist "venv\.deps_installed" (
    echo [SETUP] Installing dependencies...
    pip install --upgrade pip
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    type nul > venv\.deps_installed
) else (
    echo [INFO] Dependencies already installed
)

:: Create necessary directories
if not exist "prometheus_novel\data" mkdir prometheus_novel\data
if not exist "prometheus_novel\data\projects" mkdir prometheus_novel\data\projects
if not exist "prometheus_novel\logs" mkdir prometheus_novel\logs

:: Set PYTHONPATH
set PYTHONPATH=%CD%;%CD%\prometheus_novel;%PYTHONPATH%

echo.
echo [INFO] Starting WriterAI Web Dashboard...
echo [INFO] Dashboard: http://localhost:8080
echo [INFO] API Docs:  http://localhost:8080/docs
echo [INFO] Press Ctrl+C to stop
echo.

:: Start the application
python -m prometheus_novel.interfaces.web.app --host 0.0.0.0 --port 8080

:: Keep window open on error
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%
    pause
)
