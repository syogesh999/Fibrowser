@echo off
setlocal
cd /d "%~dp0\.."

echo ===================================================
echo   Building Fibrowser Pro v2.0.0 (Windows x64)
echo ===================================================

echo [1/2] Packaging standalone executable with PyInstaller...
py -m PyInstaller --noconfirm --onefile --windowed --name "FibrowserPro" --add-data "assets;assets" main.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo [2/2] Creating compressed ZIP archive...
powershell -Command "Compress-Archive -Path dist\FibrowserPro.exe -DestinationPath dist\FibrowserPro-v2.0.0-windows-x64.zip -Force"
if errorlevel 1 (
    echo [ERROR] ZIP compression failed!
    pause
    exit /b 1
)

echo ===================================================
echo   Build Successful!
echo   Output files located in dist\
echo     - dist\FibrowserPro.exe
echo     - dist\FibrowserPro-v2.0.0-windows-x64.zip
echo ===================================================
pause
