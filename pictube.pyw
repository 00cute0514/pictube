"""픽튜브 (PicTube) - personal-use YouTube downloader UI (tkinter, dark theme)."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import core

BG, PANEL, FG, MUTED, ACCENT, ACCENT_HI, ERR = "#16181d", "#22252c", "#e8eaee", "#9aa0ab", "#ff4d4d", "#ff6b6b", "#ff8a80"


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = core.load_config()
        self.job = None
        self.files = []
        self.busy = False
        self.q = queue.Queue()
        root.title("픽튜브")
        root.configure(bg=BG)
        root.geometry("640x520")
        root.minsize(560, 500)
        self._style()
        self._build()
        root.bind("<FocusIn>", lambda e: self._clip_fill() if e.widget is root else None)
        root.after(100, self._clip_fill)
        root.after(100, self._pump)

    # ---------- UI ----------
    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        f = ("맑은 고딕", 10)
        self.root.option_add("*Font", f)
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, font=f, bordercolor=PANEL,
                    lightcolor=PANEL, darkcolor=PANEL, troughcolor=PANEL)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("Muted.TLabel", foreground=MUTED)
        s.configure("TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=FG, padding=6)
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG, arrowcolor=FG, padding=4)
        s.map("TCombobox", fieldbackground=[("readonly", PANEL), ("disabled", BG)], foreground=[("disabled", MUTED)])
        s.configure("TButton", background=PANEL, foreground=FG, padding=(12, 6), borderwidth=0)
        s.map("TButton", background=[("active", "#2e323b"), ("disabled", BG)], foreground=[("disabled", "#5a5f69")])
        s.configure("Accent.TButton", background=ACCENT, foreground="white", font=("맑은 고딕", 11, "bold"), padding=(18, 8))
        s.map("Accent.TButton", background=[("active", ACCENT_HI), ("disabled", "#4a2a2d")], foreground=[("disabled", "#8a6a6c")])
        for w in ("TRadiobutton", "TCheckbutton"):
            s.configure(w, background=BG, foreground=FG, indicatorbackground="#3a3f4a", indicatorforeground=FG)
            s.map(w, background=[("active", BG)], indicatorbackground=[("selected", ACCENT), ("!selected", "#3a3f4a")],
                  foreground=[("disabled", MUTED)])
        s.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL, borderwidth=0, thickness=14)

    def _build(self):
        pad = {"padx": 20}
        tk.Label(self.root, text="픽튜브", bg=BG, fg=FG, font=("맑은 고딕", 20, "bold")).pack(anchor="w", pady=(16, 0), padx=18)
        ttk.Label(self.root, text="유튜브 링크를 붙여넣고 영상(MP4) 또는 소리(MP3)로 저장합니다.", style="Muted.TLabel").pack(anchor="w", **pad)

        row = ttk.Frame(self.root)
        row.pack(fill="x", pady=(14, 0), **pad)
        self.url = tk.StringVar()
        self.entry = ttk.Entry(row, textvariable=self.url)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.check())
        ttk.Button(row, text="붙여넣기", command=self.paste).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="정보 확인", command=self.check).pack(side="left", padx=(8, 0))

        self.info = tk.StringVar(value="링크를 입력하면 영상 정보가 여기에 표시됩니다.")
        ttk.Label(self.root, textvariable=self.info, style="Muted.TLabel", wraplength=590, justify="left").pack(anchor="w", pady=(10, 0), **pad)

        box = ttk.Frame(self.root)
        box.pack(fill="x", pady=(14, 0), **pad)
        self.mode = tk.StringVar(value="video")
        ttk.Radiobutton(box, text="영상 (MP4)", value="video", variable=self.mode, command=self._mode).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(box, text="소리만 (MP3)", value="audio", variable=self.mode, command=self._mode).grid(row=0, column=1, sticky="w", padx=(18, 0))
        ttk.Label(box, text="화질").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.quality = ttk.Combobox(box, values=list(core.QUALITIES), state="readonly", width=12)
        self.quality.set(self.cfg.get("quality", "최고 화질") if self.cfg.get("quality") in core.QUALITIES else "최고 화질")
        self.quality.grid(row=1, column=1, sticky="w", padx=(18, 0), pady=(10, 0))
        self.playlist = tk.BooleanVar(value=False)
        self.pl_check = ttk.Checkbutton(box, text="재생목록 전체 받기", variable=self.playlist)
        self.pl_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.pl_check.state(["disabled"])

        fr = ttk.Frame(self.root)
        fr.pack(fill="x", pady=(14, 0), **pad)
        ttk.Label(fr, text="저장 폴더").pack(side="left")
        self.outdir = tk.StringVar(value=self.cfg.get("outdir") or core.DEFAULT_DIR)
        ttk.Entry(fr, textvariable=self.outdir, state="readonly").pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(fr, text="변경", command=self.choose_dir).pack(side="left")

        self.bar = ttk.Progressbar(self.root, maximum=100)
        self.bar.pack(fill="x", pady=(20, 0), **pad)
        self.pct = tk.StringVar(value="0%")
        self.status = tk.StringVar(value="")
        st = ttk.Frame(self.root)
        st.pack(fill="x", pady=(6, 0), **pad)
        ttk.Label(st, textvariable=self.pct, width=5).pack(side="left")
        self.status_lbl = ttk.Label(st, textvariable=self.status, style="Muted.TLabel", wraplength=520, justify="left")
        self.status_lbl.pack(side="left", fill="x", expand=True)

        btns = ttk.Frame(self.root)
        btns.pack(fill="x", pady=(16, 16), **pad)
        self.btn_go = ttk.Button(btns, text="다운로드", style="Accent.TButton", command=self.start)
        self.btn_go.pack(side="left")
        self.btn_cancel = ttk.Button(btns, text="취소", command=self.cancel, state="disabled")
        self.btn_cancel.pack(side="left", padx=(8, 0))
        self.btn_open = ttk.Button(btns, text="폴더 열기", command=self.open_folder, state="disabled")
        self.btn_open.pack(side="left", padx=(8, 0))
        self.btn_upd = ttk.Button(btns, text="엔진 업데이트", command=self.update_engine)
        self.btn_upd.pack(side="right")
        self._mode()

    def _mode(self):
        self.quality.configure(state="readonly" if self.mode.get() == "video" else "disabled")

    # ---------- helpers ----------
    def set_progress(self, pct, text, error=False):
        self.bar["value"] = pct
        self.pct.set(f"{pct}%")
        self.status.set(text)
        self.status_lbl.configure(foreground=ERR if error else MUTED)

    def set_busy(self, busy):
        self.busy = busy
        self.btn_go.configure(state="disabled" if busy else "normal")
        self.btn_upd.configure(state="disabled" if busy else "normal")
        self.btn_cancel.configure(state="normal" if busy else "disabled")

    def _clip_fill(self):
        if self.busy or self.url.get().strip():
            return
        try:
            text = self.root.clipboard_get().strip()
        except tk.TclError:
            return
        if core.is_youtube_url(text):
            self.url.set(text)
            self.check()

    def paste(self):
        try:
            self.url.set(self.root.clipboard_get().strip())
        except tk.TclError:
            return
        self.check()

    def choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.outdir.get() if os.path.isdir(self.outdir.get()) else None, title="저장 폴더 선택")
        if d:
            self.outdir.set(os.path.normpath(d))
            self.cfg["outdir"] = self.outdir.get()
            core.save_config(self.cfg)

    def open_folder(self):
        d = self.outdir.get()
        os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def _run_bg(self, fn):
        threading.Thread(target=lambda: self.q.put(fn()), daemon=True).start()

    def _pump(self):
        try:
            while True:
                self.q.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    # ---------- actions ----------
    def check(self):
        url = self.url.get().strip()
        if not core.is_youtube_url(url):
            self.info.set("유튜브 링크가 아닙니다. (youtube.com / youtu.be 주소만 지원)")
            return
        has_video, has_list = core.url_kind(url)
        if has_list:
            self.pl_check.state(["!disabled"])
            if not has_video:
                self.playlist.set(True)
                self.pl_check.state(["disabled"])
        else:
            self.playlist.set(False)
            self.pl_check.state(["disabled"])
        self.info.set("영상 정보를 가져오는 중...")

        def work():
            try:
                i = core.fetch_info(url)
            except core.DownloadError as e:
                return lambda: self.url.get().strip() == url and self.info.set(str(e))
            except Exception as e:
                return lambda: self.info.set(f"정보를 가져오지 못했습니다. ({e})")

            def show():
                if self.url.get().strip() != url:
                    return
                if i["playlist"]:
                    self.info.set(f"재생목록: {i['title']} ({i['count']}개)")
                else:
                    d = i["duration"] or 0
                    dur = f"{d // 60}:{d % 60:02d}" if d < 3600 else f"{d // 3600}:{d % 3600 // 60:02d}:{d % 60:02d}"
                    best = f" · 최대 {i['max_height']}p" if i["max_height"] else ""
                    self.info.set(f"{i['title']}\n{i['uploader']} · {dur}{best}")
            return show
        self._run_bg(work)

    def start(self):
        url = self.url.get().strip()
        if not core.is_youtube_url(url):
            self.set_progress(0, "유튜브 링크를 먼저 입력해 주세요.", error=True)
            return
        self.cfg.update(outdir=self.outdir.get(), quality=self.quality.get())
        core.save_config(self.cfg)
        audio = self.mode.get() == "audio"
        playlist = bool(self.playlist.get())
        job = self.job = core.Job()
        self.files = []
        self.btn_open.configure(state="disabled")
        self.set_busy(True)
        self.set_progress(0, "시작하는 중...")

        def work():
            try:
                files = job.run(url, self.outdir.get(), self.quality.get(), audio, playlist,
                                lambda p, t: self.q.put(lambda: self.set_progress(p, t)))
            except core.DownloadError as e:
                return lambda: self._done(None, str(e))
            except Exception as e:
                return lambda: self._done(None, f"예상하지 못한 오류가 발생했습니다.\n({e})")
            return lambda: self._done(files, None)
        self._run_bg(work)

    def _done(self, files, err):
        self.set_busy(False)
        if err:
            self.set_progress(0, err, error=True)
            return
        self.files = files
        self.set_progress(100, f"완료: {os.path.basename(files[-1])}" if files else "완료")
        self.btn_open.configure(state="normal")

    def cancel(self):
        if self.job:
            self.status.set("취소하는 중...")
            self.job.cancel()

    def update_engine(self):
        self.set_busy(True)
        self.btn_cancel.configure(state="disabled")
        self.set_progress(0, "엔진을 업데이트하는 중...")

        def work():
            ok, out = core.update_engine()

            def done():
                self.set_busy(False)
                last = out.splitlines()[-1] if out else ""
                if ok:
                    self.set_progress(0, "엔진 업데이트 확인 완료.\n" + last)
                else:
                    self.set_progress(0, "엔진 업데이트에 실패했습니다.\n" + last, error=True)
            return done
        self._run_bg(work)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
