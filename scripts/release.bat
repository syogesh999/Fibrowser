@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo ================================================================
echo   🚀 FIBROWSER PRO - ONE-CLICK GITHUB AUTO-RELEASE TOOL
echo ================================================================
echo.

:: Get current version from config.py using Python
for /f "delims=" %%v in ('py -c "from fibrowser.config import APP_VERSION; print(APP_VERSION)" 2^>nul') do set CURRENT_VERSION=%%v

if "%CURRENT_VERSION%"=="" set CURRENT_VERSION=2.1.0

echo Current Version detected: v%CURRENT_VERSION%
echo.
set /p NEW_VERSION="Enter version tag to release [Press Enter for v%CURRENT_VERSION%]: "

if "%NEW_VERSION%"=="" set NEW_VERSION=%CURRENT_VERSION%
:: Remove leading 'v' if user typed it
if "%NEW_VERSION:~0,1%"=="v" set NEW_VERSION=%NEW_VERSION:~1%
if "%NEW_VERSION:~0,1%"=="V" set NEW_VERSION=%NEW_VERSION:~1%

set TAG=v%NEW_VERSION%

echo.
echo ================================================================
echo   Target Release Tag: %TAG%
echo ================================================================
echo.

:: Step 1: Build local executable and ZIP archive
echo [1/4] Building standalone Windows executable and Installer...
py -m PyInstaller --noconfirm --onefile --windowed --name "FibrowserPro" --icon "assets/icons/fibrowser.ico" --add-data "assets;assets" main.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

py -m PyInstaller --noconfirm FibrowserInstaller.spec
if errorlevel 1 (
    echo [ERROR] FibrowserInstaller build failed!
    pause
    exit /b 1
)

powershell -Command "Compress-Archive -Path dist\FibrowserPro.exe -DestinationPath dist\FibrowserPro-%TAG%-windows-x64.zip -Force"
powershell -Command "Compress-Archive -Path dist\FibrowserInstaller.exe -DestinationPath dist\FibrowserInstaller-%TAG%-windows-x64.zip -Force"

:: Step 2: Stage and commit all changes
echo.
echo [2/4] Committing code changes...
git add -A
git commit -m "Release %TAG%: Automated release build with enhancements" --allow-empty

:: Step 3: Create annotated tag
echo.
echo [3/4] Creating and updating release tag %TAG%...
git tag -f -a %TAG% -m "Release %TAG% for Fibrowser Pro"

:: Step 4: Push branch and tag to GitHub to trigger automatic release
echo.
echo [4/4] Pushing to GitHub (Triggers GitHub Actions Auto-Release)...
git push origin dev main --tags -f

if errorlevel 1 (
    echo [ERROR] Git push failed. Check your internet connection or GitHub credentials.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   🎉 RELEASE TRIGGERED SUCCESSFULLY!
echo ================================================================
echo.
echo GitHub Actions is now automatically:
echo   1. Building the release binaries in the cloud
echo   2. Creating the GitHub Release for %TAG%
echo   3. Attaching the .exe, installer, and .zip files to the release page
echo.
echo Check live progress at:
echo   https://github.com/syogesh999/Fibrowser/actions
echo.
echo Your release will appear at:
echo   https://github.com/syogesh999/Fibrowser/releases
echo ================================================================
echo.
pause
