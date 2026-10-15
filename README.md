# 픽튜브 (PicTube)

개인 용도의 Windows용 유튜브 영상·소리 저장 도구입니다. 링크를 붙여넣고 MP4(화질 선택) 또는 MP3로 저장합니다.

## 설치

[Releases](../../releases/latest)에서 `PicTube-Setup-<버전>.exe`를 받아 실행합니다.
설치 중에 앱 본체(이 저장소의 릴리스), [yt-dlp](https://github.com/yt-dlp/yt-dlp)(공식 릴리스), [FFmpeg](https://www.gyan.dev/ffmpeg/builds/)(gyan.dev 빌드)를 받고, 설치 파일에 고정된 SHA-256으로 검증합니다.

## 사용 시 유의

본인이 권리를 가졌거나 저장이 허락된 콘텐츠에만 사용하세요. YouTube 서비스 약관과 저작권법을 지키는 것은 사용자의 책임입니다.

## 직접 빌드

```powershell
.\fetch-engines.ps1      # bin\ 에 yt-dlp, ffmpeg 받기 (SHA-256 검증)
.\make-release.ps1       # PicTube.exe, 앱 zip, 설치 프로그램 빌드 (PyInstaller, Inno Setup 6 필요)
```
