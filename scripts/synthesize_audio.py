#!/usr/bin/env python3
"""一枚物の音声スクリプトを TTS で合成し、単一の MP3 に連結する。

対応 TTS: OpenAI 互換 API を持つ任意のサーバー (デフォルト: irodori-speech-server)。

使い方:
    python3 scripts/synthesize_audio.py demo/audio_scripts/narration.txt
    python3 scripts/synthesize_audio.py script.txt out.mp3

スクリプトはプレーンテキスト。セクション区切りは独行の `[[PAUSE 1.5]]` で、
そのセクション音声の後ろに指定秒数の無音を挿入する (1.0 / 1.5 / 2.0)。

各セクションは POST /v1/audio/speech に送る。声質は Voice Design caption
(環境変数 IRODORI_CAPTION) で指定する参照音声なしボイスデザイン。
出力は mono 64kbps MP3。セクションは ffmpeg で 1 ファイルに連結する。

環境変数:
    IRODORI_BASE_URL  TTS サーバー URL (既定 http://localhost:8088)
    IRODORI_MODEL     モデル名 (既定 irodori-tts)
    IRODORI_CAPTION   声質指定 caption (既定: 落ち着いた女性の声)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("IRODORI_BASE_URL", "http://localhost:8088")
MODEL = os.environ.get("IRODORI_MODEL", "irodori-tts")
CAPTION = os.environ.get(
    "IRODORI_CAPTION",
    "落ち着いた低めの女性の声。丁寧で穏やかな話し方。数字や名称はゆっくり明瞭に読む。",
)
BITRATE = os.environ.get("AUDIO_BITRATE", "64k")
PAUSE = re.compile(r"^\[\[PAUSE (1\.0|1\.5|2\.0)\]\]$")
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def sections(text):
    """スクリプトを (本文, 後続の無音秒数) の対に分割する."""
    parts = []
    current = []
    for line in text.splitlines():
        m = PAUSE.match(line.strip())
        if m:
            if current:
                parts.append(("\n".join(current), float(m.group(1))))
                current = []
        elif line.strip():
            current.append(line.strip())
    if current:
        parts.append(("\n".join(current), 0.0))
    return parts


def speech(text, out, base_url=BASE_URL):
    body = json.dumps(
        {
            "model": MODEL,
            "input": text,
            "voice": "none",
            "response_format": "wav",
            "irodori": {"caption": CAPTION},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/v1/audio/speech",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        content = urllib.request.urlopen(req, timeout=600).read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"TTS failed ({exc.code}): {exc.read().decode()[:200]}")
    wav = out.with_suffix(".wav")
    wav.write_bytes(content)
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
         "-ac", "1", "-b:a", BITRATE, str(out)],
        check=True,
    )
    wav.unlink()
    return out


def silence(seconds, out):
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", str(seconds), "-b:a", BITRATE, str(out)],
        check=True,
    )
    return out


def main(path, out=None, base_url=BASE_URL, quiet=False):
    path = Path(path)
    out = Path(out or f"audio/{path.stem}.mp3")
    out.parent.mkdir(parents=True, exist_ok=True)
    parts = sections(path.read_text(encoding="utf-8"))
    if not parts:
        raise SystemExit("no text to synthesize")

    work = out.parent / f".{path.stem}"
    work.mkdir(exist_ok=True)
    files = []
    for i, (text, pause) in enumerate(parts, 1):
        f = speech(text, work / f"{i:03d}.mp3", base_url)
        files.append(f)
        if not quiet:
            print(f"section {i}: {len(text)} chars -> {f.name}")
        if pause:
            files.append(silence(pause, work / f"{i:03d}s.mp3"))

    listfile = work / "concat.txt"
    listfile.write_text(
        "\n".join(f"file '{f.name}'" for f in files), encoding="utf-8"
    )
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c:a", "libmp3lame", "-b:a", BITRATE, str(out)],
        check=True,
    )
    print(f"{out}: {out.stat().st_size} bytes, {len(parts)} sections")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("script")
    p.add_argument("out", nargs="?")
    a = p.parse_args()
    main(a.script, a.out)
