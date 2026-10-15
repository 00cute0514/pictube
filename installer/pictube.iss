; 픽튜브 설치 프로그램. make-release.ps1이 /D 값(주소·SHA-256)을 넣어 빌드합니다.
; 설치할 때 앱 본체는 픽튜브 GitHub 릴리스에서, yt-dlp·FFmpeg는 각 공식 배포처에서 받고
; 모두 고정된 SHA-256으로 검증합니다(불일치 시 설치 중단).

[Setup]
AppId={{6F1C2B7A-4D3E-4A8B-9C51-7E2D0B6A3F14}
AppName=픽튜브
AppVersion={#AppVersion}
AppPublisher=말사스튜디오
DefaultDirName={autopf}\PicTube
DefaultGroupName=픽튜브
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=PicTube-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\PicTube.exe
UninstallDisplayName=픽튜브

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
Source: "stage.ps1"; Flags: dontcopy
Source: "{tmp}\stage\*"; DestDir: "{app}"; Flags: external recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\픽튜브"; Filename: "{app}\PicTube.exe"
Name: "{autodesktop}\픽튜브"; Filename: "{app}\PicTube.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PicTube.exe"; Description: "픽튜브 실행"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\bin"
Type: filesandordirs; Name: "{app}\_internal"

[Code]
var
  ProgressPage: TOutputProgressWizardPage;

procedure InitializeWizard;
begin
  ProgressPage := CreateOutputProgressPage('파일 받는 중', '픽튜브와 다운로드 엔진(yt-dlp, FFmpeg)을 받고 있습니다. 1~2분 걸릴 수 있습니다.');
end;

// 다운로드·SHA-256 검증·압축 풀기는 stage.ps1(curl.exe, 실패 시 재시도)이 하고, 임시 폴더의 stage 에 설치할 파일을 만듭니다.
function NextButtonClick(CurPageID: Integer): Boolean;
var
  T, Err: AnsiString;
  Code: Integer;
begin
  Result := True;
  if CurPageID <> wpReady then exit;
  ExtractTemporaryFile('stage.ps1');
  T := ExpandConstant('{tmp}');
  ProgressPage.SetText('받는 중...', '');
  ProgressPage.ProgressBar.Style := npbstMarquee;
  ProgressPage.Show;
  try
    if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
        '-NoProfile -ExecutionPolicy Bypass -File "' + T + '\stage.ps1" -T "' + T + '"' +
        ' -AppUrl "{#AppUrl}" -AppSha {#AppSha} -YtUrl "{#YtdlpUrl}" -YtSha {#YtdlpSha} -FfUrl "{#FfUrl}" -FfSha {#FfSha}',
        '', SW_HIDE, ewWaitUntilTerminated, Code) or (Code <> 0) then
    begin
      if not LoadStringFromFile(T + '\stage-error.txt', Err) then Err := '';
      SuppressibleMsgBox('파일을 받지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.' + #13#10#13#10 + String(Err), mbCriticalError, MB_OK, IDOK);
      Result := False;
    end;
  finally
    ProgressPage.Hide;
  end;
end;
