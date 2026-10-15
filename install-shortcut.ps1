# 바탕화면에 "픽튜브" 바로가기를 만듭니다. (pythonw.exe로 pictube.pyw 실행, 콘솔 창 없음)
$ErrorActionPreference = 'Stop'
# build-exe.ps1로 만든 PicTube.exe가 있으면 그것을, 없으면 pythonw로 pictube.pyw를 실행합니다.
$exe = Join-Path $PSScriptRoot 'dist\PicTube\PicTube.exe'
$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) '픽튜브.lnk'
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
if (Test-Path $exe) {
    $s.TargetPath = $exe
    $s.WorkingDirectory = Split-Path $exe
} else {
    $app = Join-Path $PSScriptRoot 'pictube.pyw'
    if (-not (Test-Path $app)) { throw "pictube.pyw not found: $app" }
    $s.TargetPath = (Get-Command pythonw.exe -ErrorAction Stop).Source
    $s.Arguments = '"' + $app + '"'
    $s.WorkingDirectory = $PSScriptRoot
}
$s.Description = '픽튜브 - 유튜브 다운로더'
$s.Save()
Write-Host "Created: $lnk"
