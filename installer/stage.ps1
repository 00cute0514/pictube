# Run by the installer: downloads (curl.exe with retries), verifies pinned SHA-256, and unpacks
# into $T\stage (PicTube.exe, _internal, bin). On failure writes the reason to $T\stage-error.txt and exits 1.
param(
    [Parameter(Mandatory)][string]$T,
    [Parameter(Mandatory)][string]$AppUrl, [Parameter(Mandatory)][string]$AppSha,
    [Parameter(Mandatory)][string]$YtUrl, [Parameter(Mandatory)][string]$YtSha,
    [Parameter(Mandatory)][string]$FfUrl, [Parameter(Mandatory)][string]$FfSha)
$ErrorActionPreference = 'Stop'
trap { Set-Content -LiteralPath (Join-Path $T 'stage-error.txt') -Value "$_" -Encoding ASCII; exit 1 }

function Get-Verified($url, $name, $sha) {
    $out = Join-Path $T $name
    curl.exe -sSL --fail --retry 3 --retry-all-errors --retry-delay 2 -o $out $url
    if ($LASTEXITCODE -ne 0) { throw "Download failed (curl $LASTEXITCODE): $url" }
    $actual = (Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $sha.ToLower()) { Remove-Item -LiteralPath $out; throw "SHA-256 mismatch: $name" }
}
Get-Verified $AppUrl 'app.zip' $AppSha
Get-Verified $YtUrl 'yt-dlp.exe' $YtSha
Get-Verified $FfUrl 'ffmpeg.zip' $FfSha

$stage = Join-Path $T 'stage'
$bin = Join-Path $stage 'bin'
$ff = Join-Path $T 'ff'
New-Item -ItemType Directory -Force $bin, $ff | Out-Null
tar -xf (Join-Path $T 'app.zip') -C $stage
if ($LASTEXITCODE -ne 0) { throw 'app.zip extract failed' }
Move-Item (Join-Path $T 'yt-dlp.exe') $bin -Force
tar -xf (Join-Path $T 'ffmpeg.zip') -C $ff
if ($LASTEXITCODE -ne 0) { throw 'ffmpeg.zip extract failed' }
foreach ($n in 'ffmpeg.exe', 'ffprobe.exe') {
    $x = Get-ChildItem $ff -Recurse -Filter $n | Select-Object -First 1
    if (-not $x) { throw "$n missing in ffmpeg.zip" }
    Copy-Item $x.FullName $bin -Force
}
if (-not (Test-Path (Join-Path $stage 'PicTube.exe'))) { throw 'PicTube.exe missing in app.zip' }
