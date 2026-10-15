# Builds the release assets: dist\PicTube-app.zip (app without engines) and installer\Output\PicTube-Setup-<ver>.exe.
# The installer pins the app zip, yt-dlp and FFmpeg to exact versions + SHA-256.
param([string]$Version = '1.0.0', [string]$Repo = '00cute0514/pictube')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Get-Text($u) { $c = (Invoke-WebRequest $u -UseBasicParsing).Content; if ($c -is [byte[]]) { [Text.Encoding]::UTF8.GetString($c) } else { $c } }
& .\build-exe.ps1

$app = 'dist\PicTube-app.zip'
Compress-Archive -Path dist\PicTube\PicTube.exe, dist\PicTube\_internal -DestinationPath $app -Force
$appSha = (Get-FileHash $app -Algorithm SHA256).Hash.ToLower()

# yt-dlp: the version in bin\, hash from that tag's official SHA2-256SUMS
$yv = (& bin\yt-dlp.exe --version).Trim()
$ybase = "https://github.com/yt-dlp/yt-dlp/releases/download/$yv"
$sums = Get-Text "$ybase/SHA2-256SUMS"
if ($sums -notmatch '(?m)^([0-9a-f]{64})\s+yt-dlp\.exe\s*$') { throw 'yt-dlp.exe not in SHA2-256SUMS' }
$ySha = $Matches[1]

# FFmpeg: gyan.dev versioned package, hash from gyan.dev's published release sha256 for the same version
$fv = (Get-Text 'https://www.gyan.dev/ffmpeg/builds/release-version').Trim()
$fSha = ((Get-Text 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256').Trim() -split '\s+')[0].ToLower()
if ($fSha -notmatch '^[0-9a-f]{64}$') { throw 'bad ffmpeg sha256' }
$fUrl = "https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-$fv-essentials_build.zip"

$iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
& $iscc /Q "/DAppVersion=$Version" "/DAppUrl=https://github.com/$Repo/releases/download/v$Version/PicTube-app.zip" "/DAppSha=$appSha" `
    "/DYtdlpUrl=$ybase/yt-dlp.exe" "/DYtdlpSha=$ySha" "/DFfUrl=$fUrl" "/DFfSha=$fSha" installer\pictube.iss
if ($LASTEXITCODE -ne 0) { throw 'ISCC failed' }
Write-Host "app.zip sha256=$appSha  yt-dlp $yv  ffmpeg $fv"
Write-Host "Built: $PSScriptRoot\$app and $PSScriptRoot\installer\Output\PicTube-Setup-$Version.exe"
