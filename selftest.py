"""Downloads a short public video via the app's own core.Job (720p MP4, then MP3) and ffprobes the results.
Usage: python selftest.py [outdir]"""
import json
import os
import subprocess
import sys
import tempfile

import core

URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
out = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="pictube-test-")
last = [-1]


def prog(p, t):
    if p != last[0] and p % 10 == 0:
        last[0] = p
        print(f"  {p:3d}% {t}")


def probe(path):
    p = subprocess.run([os.path.join(core.BIN, "ffprobe.exe"), "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


ok = True
for label, audio in (("MP4 720p", False), ("MP3", True)):
    print(label)
    files = core.Job().run(URL, out, "720p", audio, False, prog)
    for f in files:
        info = probe(f)
        kinds = [s["codec_type"] for s in info["streams"]]
        good = ("audio" in kinds) and (audio != ("video" in kinds)) if audio else {"audio", "video"} <= set(kinds)
        ok &= good
        print(f"  file={f}\n  size={os.path.getsize(f)} bytes streams={info['streams']} duration={info['format']['duration']} -> {'OK' if good else 'FAIL'}")
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
