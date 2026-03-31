@echo off
title Woods Comfort Systems - Forms App
color 0A

cd /d "%~dp0"

echo ============================================================
echo    Woods Comfort Systems - Forms Application (Dev Mode)
echo ============================================================
echo.

REM Clear Python cache to ensure fresh templates
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "templates\__pycache__" rmdir /s /q "templates\__pycache__"

echo Starting server...
echo.

python app.py

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Failed to start the application.
    echo Make sure Python is installed and in your PATH.
    echo.
    pause
)
