# Build script for Fibrowser Pro (PowerShell)
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Building Fibrowser Pro (Windows x64)" -ForegroundColor Cyan
Write-Host "  Root Directory: $ProjectRoot" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

Write-Host "`n[1/3] Packaging standalone executable with PyInstaller..." -ForegroundColor Yellow
py -m PyInstaller --noconfirm --onefile --windowed --name "FibrowserPro" --icon "assets/icons/fibrowser.ico" --add-data "assets;assets" main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller build failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[2/4] Building installer (bundles FibrowserPro.exe inside)..." -ForegroundColor Yellow
py -m PyInstaller --noconfirm FibrowserInstaller.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] FibrowserInstaller build failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[3/4] Creating compressed ZIP archive for standalone app..." -ForegroundColor Yellow
Compress-Archive -Path "dist\FibrowserPro.exe" -DestinationPath "dist\FibrowserPro-v2.0.0-windows-x64.zip" -Force

Write-Host "`n[4/4] Creating compressed ZIP archive for installer..." -ForegroundColor Yellow
Compress-Archive -Path "dist\FibrowserInstaller.exe" -DestinationPath "dist\FibrowserInstaller-v2.0.0-windows-x64.zip" -Force

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "  Build Successful!" -ForegroundColor Green
Write-Host "  Outputs created in dist/:" -ForegroundColor Green
Write-Host "    - dist\FibrowserPro.exe          (standalone app)" -ForegroundColor White
Write-Host "    - dist\FibrowserInstaller.exe     (installer with bundled app)" -ForegroundColor White
Write-Host "    - dist\FibrowserPro-v2.0.0-windows-x64.zip" -ForegroundColor White
Write-Host "    - dist\FibrowserInstaller-v2.0.0-windows-x64.zip" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Green
