@echo off
title Gridiron GM
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo First launch: setting up Gridiron GM. This takes a minute, once.
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo Could not find Python. Install it from python.org and tick "Add python.exe to PATH".
        pause
        exit /b 1
    )
)

"venv\Scripts\python.exe" -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo Installing PyQt6...
    "venv\Scripts\python.exe" -m pip install --upgrade pip
    "venv\Scripts\python.exe" -m pip install PyQt6
    if errorlevel 1 (
        echo.
        echo PyQt6 failed to install. Check your internet connection and try again.
        pause
        exit /b 1
    )
)

"venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo The game closed with an error. Details are in gridiron_errors.log in this folder.
    pause
)
