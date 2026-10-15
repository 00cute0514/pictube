# Builds dist\PicTube\PicTube.exe (no Python needed to run) and dist\PicTube.zip.
# Requires: pip install pyinstaller, and bin\ filled by fetch-engines.ps1.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
foreach ($f in 'yt-dlp.exe', 'ffmpeg.exe', 'ffprobe.exe') { if (-not (Test-Path "bin\$f")) { throw "bin\$f missing: run fetch-engines.ps1" } }
python -m PyInstaller --noconfirm --clean --windowed --onedir --name PicTube pictube.pyw
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
Copy-Item bin -Destination dist\PicTube\bin -Recurse -Force
Compress-Archive -Path dist\PicTube -DestinationPath dist\PicTube.zip -Force
Write-Host "Built: $PSScriptRoot\dist\PicTube\PicTube.exe"
