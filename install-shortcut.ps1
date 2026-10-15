# 바탕화면에 "픽튜브" 바로가기를 만듭니다. (pythonw.exe로 pictube.pyw 실행, 콘솔 창 없음)
$ErrorActionPreference = 'Stop'
$pyw = (Get-Command pythonw.exe -ErrorAction Stop).Source
$app = Join-Path $PSScriptRoot 'pictube.pyw'
if (-not (Test-Path $app)) { throw "pictube.pyw not found: $app" }
$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) '픽튜브.lnk'
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = $pyw
$s.Arguments = '"' + $app + '"'
$s.WorkingDirectory = $PSScriptRoot
$s.Description = '픽튜브 - 유튜브 다운로더'
$s.Save()
Write-Host "Created: $lnk"
