@echo off
setlocal
cd /d "%~dp0\.."

echo ===================================================
echo   Building Fibrowser Pro v2.0.0 (Windows x64)
echo ===================================================

echo [1/3] Packaging standalone browser executable with PyInstaller...
py -m PyInstaller --noconfirm --onefile --windowed --name "FibrowserPro" --icon "assets/icons/fibrowser.ico" --add-data "assets;assets" main.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo [2/3] Packaging installer wizard with bundled FibrowserPro.exe...
py -m PyInstaller --noconfirm FibrowserInstaller.spec
if errorlevel 1 (
    echo [WARNING] Installer build failed, continuing...
)

echo [3/3] Creating compressed ZIP archives...
powershell -Command "Compress-Archive -Path dist\FibrowserPro.exe -DestinationPath dist\FibrowserPro-v2.0.0-windows-x64.zip -Force"
powershell -Command "if (Test-Path dist\FibrowserInstaller.exe) { Compress-Archive -Path dist\FibrowserInstaller.exe -DestinationPath dist\FibrowserInstaller-v2.0.0-windows-x64.zip -Force }"

echo ===================================================
echo   Build Successful!
echo   Output files located in dist\
echo     - dist\FibrowserPro.exe
echo     - dist\FibrowserInstaller.exe
echo     - dist\FibrowserPro-v2.0.0-windows-x64.zip
echo     - dist\FibrowserInstaller-v2.0.0-windows-x64.zip
echo ===================================================
pause
