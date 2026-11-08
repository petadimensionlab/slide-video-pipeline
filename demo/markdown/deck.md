---
marp: true
theme: default
paginate: true
lang: ja
style: |
  section { font-family: "Noto Sans CJK JP", sans-serif; font-size: 30px;
            background: white; color: #111; padding: 40px 70px; }
  h1 { color: #1a5fb4; font-size: 44px; margin-bottom: 10px; }
  h2 { color: #1a5fb4; font-size: 34px; }
  ul { font-size: 28px; line-height: 1.6; }
  table { font-size: 24px; }
---

# デモ: 音声付きスライド動画の作り方

- Marp スライド + 日本語ナレーション + TTS + Remotion
- この 4 枚のデッキがそのままデモ素材です

---

## ステップ 1 — 台本とスライドを 1:1 に対応させる

- スライド 1 枚 = ナレーション 1 ブロック
- 音声スクリプトは `[[PAUSE 1.5]]` でセクション区切り
- 動画スクリプトは `===` でブロック区切り

---

## ステップ 2 — 音声合成とタイミング計測

| 成果物 | 作り方 |
|---|---|
| スライド PNG | Marp CLI `--images png` |
| セクション音声 | TTS API → MP3 (mono 64kbps) |
| timing.json | 音声実測長 + 余白 1.2 秒 → フレーム数 |

---

## ステップ 3 — Remotion で動画化

- `timing.json` に従い、音声 1 ブロック = 1 スライドで再生
- `remotion render Demo out/demo.mp4`
- 音声だけ / 動画だけ、どちらだけでも出力できます
