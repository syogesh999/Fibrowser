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

Write-Host "`n[2/3] Packaging installer wizard with PyInstaller..." -ForegroundColor Yellow
py -m PyInstaller --noconfirm --onefile --windowed --name "FibrowserInstaller" --icon "assets/icons/fibrowser.ico" --add-data "assets;assets" installer.py

Write-Host "`n[3/3] Creating compressed ZIP archive..." -ForegroundColor Yellow
if (Test-Path "dist\FibrowserInstaller.exe") {
    Compress-Archive -Path "dist\FibrowserPro.exe", "dist\FibrowserInstaller.exe" -DestinationPath "dist\FibrowserPro-v2.0.0-windows-x64.zip" -Force
} else {
    Compress-Archive -Path "dist\FibrowserPro.exe" -DestinationPath "dist\FibrowserPro-v2.0.0-windows-x64.zip" -Force
}

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "  Build Successful!" -ForegroundColor Green
Write-Host "  Outputs created in dist/:" -ForegroundColor Green
Write-Host "    - dist\FibrowserPro.exe" -ForegroundColor White
Write-Host "    - dist\FibrowserInstaller.exe" -ForegroundColor White
Write-Host "    - dist\FibrowserPro-v2.0.0-windows-x64.zip" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Green
