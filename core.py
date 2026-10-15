"""PicTube core: builds yt-dlp argument lists and runs downloads. No UI imports."""
import json
import os
import re
import subprocess
import threading
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(BASE, "bin")
YTDLP = os.path.join(BIN, "yt-dlp.exe")
FFMPEG_DIR = BIN
CFG_PATH = os.path.join(os.environ.get("APPDATA", BASE), "PicTube", "config.json")
DEFAULT_DIR = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Downloads", "PicTube")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# label -> max height (None = best)
QUALITIES = {"최고 화질": None, "1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
COMMON = ["--ignore-config", "--no-colors", "--encoding", "utf-8", "--windows-filenames"]


class DownloadError(Exception):
    pass


def load_config():
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False)


def is_youtube_url(text):
    t = (text or "").strip()
    if re.search(r"\s", t):
        return False
    try:
        u = urlparse(t)
    except ValueError:
        return False
    return u.scheme in ("http", "https") and (u.hostname or "").lower() in YT_HOSTS


def url_kind(url):
    """Returns (has_video, has_list)."""
    u = urlparse(url)
    q = parse_qs(u.query)
    has_list = "list" in q
    has_video = "v" in q or u.hostname.endswith("youtu.be") or u.path.startswith(("/shorts/", "/live/", "/embed/"))
    return has_video, has_list


def build_info_args(url, playlist_only=False):
    mode = ["--flat-playlist", "--yes-playlist"] if playlist_only else ["--no-playlist"]
    return [YTDLP, *COMMON, "--no-warnings", "-J", *mode, "--", url]


def build_download_args(url, outdir, quality, audio_only, playlist):
    args = [YTDLP, *COMMON, "--newline", "--ffmpeg-location", FFMPEG_DIR, "-P", outdir,
            "--progress-template", "download:PTP|%(progress.downloaded_bytes)s|%(progress.total_bytes)s|"
            "%(progress.total_bytes_estimate)s|%(progress.speed)s",
            "--print", "after_move:PTF|%(filepath)s", "--no-quiet", "--progress"]
    if playlist:
        args += ["--yes-playlist", "--ignore-errors", "-o", "%(playlist_title)s/%(playlist_index)03d - %(title)s [%(id)s].%(ext)s"]
    else:
        args += ["--no-playlist", "-o", "%(title)s [%(id)s].%(ext)s"]
    if audio_only:
        args += ["-f", "ba/b", "-x", "--audio-format", "mp3", "--audio-quality", "0"]
    else:
        h = QUALITIES[quality]
        flt = f"[height<={h}]" if h else ""
        args += ["-f", f"bv*{flt}+ba/b{flt}", "-S", "res,vcodec:h264,acodec:m4a", "--merge-output-format", "mp4"]
    return args + ["--", url]


def fetch_info(url):
    """Returns dict(title, uploader, duration, max_height, count, playlist) or raises DownloadError."""
    has_video, has_list = url_kind(url)
    playlist_only = has_list and not has_video
    p = subprocess.run(build_info_args(url, playlist_only), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    if p.returncode != 0:
        raise DownloadError(korean_error(p.stdout + p.stderr))
    d = json.loads(p.stdout)
    info = {"title": d.get("title") or "(제목 없음)", "uploader": d.get("uploader") or d.get("channel") or "",
            "duration": d.get("duration"), "playlist": playlist_only, "count": len(d.get("entries") or []),
            "max_height": max([f.get("height") or 0 for f in d.get("formats") or []] or [0])}
    return info


def korean_error(text):
    t = text or ""
    rules = [
        (r"Unsupported URL|is not a valid URL", "지원하지 않는 주소입니다. 유튜브 링크를 확인해 주세요."),
        (r"Private video", "비공개 영상이라 받을 수 없습니다."),
        (r"confirm your age|age-restricted|Sign in to confirm", "로그인이 필요한 영상(연령 제한 등)이라 받을 수 없습니다."),
        (r"video is unavailable|Video unavailable|has been removed|no longer available|does not exist", "삭제되었거나 볼 수 없는 영상입니다."),
        (r"not available in your country|blocked it in your country", "현재 지역에서는 볼 수 없는 영상입니다."),
        (r"live event|is live|This live", "라이브 방송은 받을 수 없습니다. 방송이 끝난 뒤 시도해 주세요."),
        (r"HTTP Error 403|HTTP Error 429", "유튜브가 요청을 막았습니다. 잠시 후 다시 시도하거나 '엔진 업데이트'를 눌러 보세요."),
        (r"getaddrinfo|urlopen error|Temporary failure|timed out|Connection|Unable to download", "인터넷 연결을 확인해 주세요."),
        (r"ffmpeg.*not found|ffprobe.*not found|Postprocessing", "FFmpeg 처리에 실패했습니다. bin 폴더의 ffmpeg.exe를 확인해 주세요."),
        (r"No space left|Errno 28", "저장 공간이 부족합니다."),
        (r"Permission denied|Errno 13", "저장 폴더에 쓸 수 없습니다. 다른 폴더를 선택해 주세요."),
        (r"Requested format is not available", "선택한 화질을 받을 수 없습니다. 다른 화질을 선택해 보세요."),
    ]
    for pat, msg in rules:
        if re.search(pat, t, re.I):
            return msg
    last = [l for l in t.splitlines() if l.startswith("ERROR")]
    return "다운로드에 실패했습니다." + (f"\n({last[-1][:200]})" if last else "")


class Job:
    """One download. Call run() in a worker thread; cancel() from any thread."""

    def __init__(self):
        self.proc = None
        self.cancelled = False
        self._lock = threading.Lock()

    def cancel(self):
        with self._lock:
            self.cancelled = True
            if self.proc and self.proc.poll() is None:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                               capture_output=True, creationflags=NO_WINDOW)

    def run(self, url, outdir, quality, audio_only, playlist, on_progress):
        """on_progress(percent:int, text:str). Returns list of output files; raises DownloadError."""
        os.makedirs(outdir, exist_ok=True)
        args = build_download_args(url, outdir, quality, audio_only, playlist)
        # (start, end) percent range of the bar for 1st / 2nd downloaded stream
        ranges = [(0, 90)] if audio_only else [(0, 85), (85, 95)]
        stream, item, files, log = -1, "", [], []
        with self._lock:
            if self.cancelled:
                raise DownloadError("취소했습니다.")
            self.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                         encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        for line in self.proc.stdout:
            line = line.rstrip()
            log.append(line)
            if line.startswith("PTP|"):
                _, done, total, est, speed = (line.split("|") + [""] * 5)[:5]
                tot = next((float(x) for x in (total, est) if re.fullmatch(r"[\d.]+", x)), 0)
                frac = min(float(done) / tot, 1.0) if tot and re.fullmatch(r"[\d.]+", done) else 0
                lo, hi = ranges[min(max(stream, 0), len(ranges) - 1)]
                txt = f"{item}받는 중 {frac * 100:.0f}%"
                if tot:
                    txt += f" · {float(done) / 1048576:.1f} / {tot / 1048576:.1f} MB"
                if re.fullmatch(r"[\d.]+", speed):
                    txt += f" · {float(speed) / 1048576:.1f} MB/s"
                on_progress(int(lo + (hi - lo) * frac), txt)
            elif line.startswith("PTF|"):
                files.append(line[4:])
            elif line.startswith("[download] Destination:"):
                stream += 1
            elif m := re.match(r"\[download\] Downloading item (\d+) of (\d+)", line):
                stream, item = -1, f"({m[1]}/{m[2]}) "
            elif line.startswith(("[Merger]", "[ExtractAudio]", "[VideoRemuxer]")):
                on_progress(97, item + ("MP3로 변환 중..." if "Extract" in line else "영상과 소리를 합치는 중..."))
        code = self.proc.wait()
        if self.cancelled:
            raise DownloadError("취소했습니다.")
        if code != 0 and not files:
            raise DownloadError(korean_error("\n".join(log)))
        on_progress(100, "완료")
        return files


def update_engine():
    """Runs official `yt-dlp -U`. Returns (ok, message)."""
    p = subprocess.run([YTDLP, "--ignore-config", "--no-colors", "--encoding", "utf-8", "-U"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    out = (p.stdout + p.stderr).strip()
    return p.returncode == 0, out
