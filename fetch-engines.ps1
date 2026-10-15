# Downloads yt-dlp.exe + ffmpeg/ffprobe into .\bin and verifies sha256. Fails loudly on mismatch.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$bin = Join-Path $PSScriptRoot 'bin'
New-Item -ItemType Directory -Force $bin | Out-Null
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('pictube-' + [guid]::NewGuid())
New-Item -ItemType Directory $tmp | Out-Null

function Get-Sha256($p) { (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower() }
function Assert-Hash($file, $expected, $label) {
    $actual = Get-Sha256 $file
    if ($actual -ne $expected.ToLower()) { throw "HASH MISMATCH for $label`n expected $expected`n actual   $actual" }
    Write-Host "OK  $label  sha256=$actual"
}

try {
    # --- yt-dlp (official GitHub release, SHA2-256SUMS) ---
    $rel = Invoke-RestMethod 'https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest'
    $base = "https://github.com/yt-dlp/yt-dlp/releases/download/$($rel.tag_name)"
    $sums = (Invoke-WebRequest "$base/SHA2-256SUMS" -UseBasicParsing).Content
    if ($sums -is [byte[]]) { $sums = [Text.Encoding]::ASCII.GetString($sums) }
    $line = $sums -split "`n" | Where-Object { $_ -match '^\s*([0-9a-fA-F]{64})\s+\*?yt-dlp\.exe\s*$' } | Select-Object -First 1
    if (-not $line) { throw 'yt-dlp.exe not found in SHA2-256SUMS' }
    $ytHash = $Matches[1]
    $ytTmp = Join-Path $tmp 'yt-dlp.exe'
    Invoke-WebRequest "$base/yt-dlp.exe" -OutFile $ytTmp -UseBasicParsing
    Assert-Hash $ytTmp $ytHash "yt-dlp.exe $($rel.tag_name)"
    Copy-Item $ytTmp (Join-Path $bin 'yt-dlp.exe') -Force

    # --- FFmpeg (gyan.dev release essentials, published .sha256) ---
    $ffUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
    $ffHashRaw = (Invoke-WebRequest "$ffUrl.sha256" -UseBasicParsing).Content
    if ($ffHashRaw -is [byte[]]) { $ffHashRaw = [Text.Encoding]::ASCII.GetString($ffHashRaw) }
    $ffHash = ($ffHashRaw.Trim() -split '\s+')[0]
    if ($ffHash -notmatch '^[0-9a-fA-F]{64}$') { throw "bad ffmpeg sha256 file content: $ffHashRaw" }
    $zip = Join-Path $tmp 'ffmpeg.zip'
    Invoke-WebRequest $ffUrl -OutFile $zip -UseBasicParsing
    Assert-Hash $zip $ffHash 'ffmpeg-release-essentials.zip'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $z = [IO.Compression.ZipFile]::OpenRead($zip)
    try {
        foreach ($e in $z.Entries) {
            if ($e.FullName -match '/bin/(ffmpeg|ffprobe)\.exe$') {
                [IO.Compression.ZipFileExtensions]::ExtractToFile($e, (Join-Path $bin $e.Name), $true)
            }
        }
    } finally { $z.Dispose() }

    Write-Host "`nVersions:"
    & (Join-Path $bin 'yt-dlp.exe') --version
    (& (Join-Path $bin 'ffmpeg.exe') -version)[0]
    Write-Host 'Done.'
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
