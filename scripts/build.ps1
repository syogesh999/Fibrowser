# Build script for Fibrowser Pro (PowerShell)
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Building Fibrowser Pro (Windows x64)" -ForegroundColor Cyan
Write-Host "  Root Directory: $ProjectRoot" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

Write-Host "`n[1/2] Packaging standalone executable with PyInstaller..." -ForegroundColor Yellow
py -m PyInstaller --noconfirm --onefile --windowed --name "FibrowserPro" --add-data "assets;assets" main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller build failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[2/2] Creating compressed ZIP archive..." -ForegroundColor Yellow
Compress-Archive -Path "dist\FibrowserPro.exe" -DestinationPath "dist\FibrowserPro-v2.0.0-windows-x64.zip" -Force

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "  Build Successful!" -ForegroundColor Green
Write-Host "  Outputs created in dist/:" -ForegroundColor Green
Write-Host "    - dist\FibrowserPro.exe" -ForegroundColor White
Write-Host "    - dist\FibrowserPro-v2.0.0-windows-x64.zip" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Green
