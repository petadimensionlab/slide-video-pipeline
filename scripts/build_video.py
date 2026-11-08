#!/usr/bin/env python3
"""スライド動画用の素材生成: セリフ1ブロックごとに TTS 音声を作り、長さを測って
timing JSON を出力する。音声1ブロック = スライド1枚の 1:1 対応を前提とする。

使い方:
    python3 scripts/build_video.py demo/audio_scripts/video_script.txt \
        "demo/slides/deck.*.png" remotion/public/demo

入力スクリプトは独行の `===` 行でセリフブロックを区切る。
ブロック番号 n が n 枚目のスライドに対応する。
先頭が `#` の行 (コメント) は合成しない。

出力: <out>/audio/NNN.mp3 と <out>/timing.json (duration_sec, frames @30fps)。
timing.json の仕様は README を参照。

環境変数:
    IRODORI_BASE_URL  TTS サーバー URL (既定 http://localhost:8088)
    IRODORI_MODEL     モデル名 (既定 irodori-tts)
    IRODORI_CAPTION   声質指定 caption
    VIDEO_FPS         動画 FPS (既定 30)
    VIDEO_GAP_SEC     音声末尾の無音余白 秒 (既定 1.2)
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("IRODORI_BASE_URL", "http://localhost:8088")
MODEL = os.environ.get("IRODORI_MODEL", "irodori-tts")
CAPTION = os.environ.get(
    "IRODORI_CAPTION",
    "落ち着いた低めの女性の声。丁寧で穏やかな話し方。数字や名称はゆっくり明瞭に読む。",
)
FPS = int(os.environ.get("VIDEO_FPS", "30"))
BITRATE = os.environ.get("AUDIO_BITRATE", "64k")
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"
GAP_SEC = float(os.environ.get("VIDEO_GAP_SEC", "1.2"))


def speech(text: str, out_mp3: Path) -> None:
    body = json.dumps(
        {"model": MODEL, "input": text, "voice": "none",
         "response_format": "wav", "irodori": {"caption": CAPTION}}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/v1/audio/speech", data=body,
        headers={"Content-Type": "application/json"},
    )
    content = urllib.request.urlopen(req, timeout=600).read()
    wav = out_mp3.with_suffix(".wav")
    wav.write_bytes(content)
    subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
         "-ac", "1", "-b:a", BITRATE, str(out_mp3)], check=True)
    wav.unlink()


def duration_sec(path: Path) -> float:
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main(script_path: str, slides_glob: str, out_dir: str) -> None:
    script = Path(script_path)
    slides = sorted(Path(".").glob(slides_glob))
    out = Path(out_dir)
    audio_dir = out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    blocks = [b.strip() for b in script.read_text(encoding="utf-8").split("\n===\n")
              if b.strip() and not all(l.strip().startswith("#") or not l.strip()
                                       for l in b.splitlines())]
    # コメント行 (先頭 #) を除去
    blocks = ["\n".join(l for l in b.splitlines() if not l.strip().startswith("#")).strip()
              for b in blocks]
    blocks = [b for b in blocks if b]

    if len(blocks) > len(slides):
        raise SystemExit(f"blocks={len(blocks)} > slides={len(slides)}")

    scenes = []
    for i, text in enumerate(blocks, 1):
        mp3 = audio_dir / f"{i:03d}.mp3"
        speech(text, mp3)
        dur = duration_sec(mp3)
        frames = round(dur * FPS) + round(GAP_SEC * FPS)
        scenes.append({
            "id": f"scene_{i:02d}",
            "slide": slides[i - 1].name,
            "audio": f"audio/{i:03d}.mp3",
            "duration_sec": round(dur, 3),
            "frames": frames,
        })
        print(f"scene {i:02d}: {len(text)} chars, {dur:.1f}s -> {frames} frames")

    timing = {"fps": FPS, "gap_sec": GAP_SEC, "scenes": scenes}
    (out / "timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(s["frames"] for s in scenes)
    print(f"{out/'timing.json'}: {len(scenes)} scenes, total {total} frames "
          f"({total / FPS:.0f}s)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:4])
