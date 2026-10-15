# Run by the installer: unpacks the verified downloads in $T into $T\stage (PicTube.exe, _internal, bin).
param([Parameter(Mandatory)][string]$T)
$ErrorActionPreference = 'Stop'
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
