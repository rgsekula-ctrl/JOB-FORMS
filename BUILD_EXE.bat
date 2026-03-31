@echo off
title Woods Comfort Systems - Build EXE
color 0A

echo ============================================================
echo    Woods Comfort Systems - Forms App Builder
echo ============================================================
echo.
echo This will create a standalone .exe file that anyone can run
echo without needing Python installed.
echo.
echo Press any key to start building...
pause > nul

cd /d "%~dp0"

echo.
echo [1/3] Installing PyInstaller...
python -m pip install pyinstaller --quiet

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Could not install PyInstaller.
    echo Make sure Python is installed correctly.
    pause
    exit /b 1
)

echo [2/3] Building executable (this may take 2-3 minutes)...

python -m PyInstaller --onefile --noconsole --name "WoodsFormsApp" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import=reportlab.graphics.barcode.code128 ^
    --hidden-import=reportlab.graphics.barcode.code39 ^
    app.py

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Build failed. Check the errors above.
    pause
    exit /b 1
)

echo.
echo [3/3] Cleaning up...
if exist "build" rmdir /s /q build
if exist "WoodsFormsApp.spec" del WoodsFormsApp.spec

echo.
echo ============================================================
echo    BUILD COMPLETE!
echo ============================================================
echo.
echo Your executable is located at:
echo    %~dp0dist\WoodsFormsApp.exe
echo.
echo Copy the "dist" folder to your server or share with others.
echo They can double-click WoodsFormsApp.exe to run the app.
echo.
echo NOTE: The first time it runs, Windows may show a security 
echo warning. Click "More info" then "Run anyway".
echo ============================================================
echo.
pause
