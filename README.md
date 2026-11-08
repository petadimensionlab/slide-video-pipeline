# slide-video-pipeline

日本語ナレーション付きスライド動画の作り方のセット。
**Marp** (Markdown → スライド PNG) + **TTS** (OpenAI 互換 API、既定は Irodori-TTS) +
**Remotion** (音声同期付き MP4 レンダリング) を結ぶスクリプトとテンプレートを同梱します。

```
Markdown デッキ ──Marp CLI──▶ スライド PNG ─┐
                                             ├─▶ Remotion ─▶ MP4
ナレーション台本 ──TTS──▶ セクション音声 ───┘
                     └──▶ 連結 MP3 (音声だけ配信用)
```

`demo/` と `remotion/public/demo/` にダミー素材 (4 枚デッキ + 実音声 + timing.json) が入っているので、
`npm install` 後 `npm run render:demo` がそのまま動きます。

## 必要環境

| 素材 | 版 / 備考 |
|---|---|
| Node.js | 18 以上 (検証: v22 / v26)。Remotion 4.0.5xx |
| ffmpeg / ffprobe | PATH 上に必要。MP3 変換・無音生成・尺測定に使用 |
| Chrome / Chrome Headless Shell | Marp CLI の PNG 出力と Remotion のレンダリングに使用 |
| Python | 3.10 以上 (スクリプトは標準ライブラリのみ) |
| TTS サーバー | OpenAI 互換 `POST /v1/audio/speech`。既定: [Irodori-TTS-Server](https://github.com/Aratako/Irodori-TTS-Server) |

## 使い方 (全体の流れ)

### 0. スライドを作る — Marp

`demo/markdown/deck.md` のような Marp フォーマットの Markdown を用意します
(先頭フロントマターに `marp: true`、スライド区切りは独行 `---`)。PNG に変換:

```bash
npx --yes @marp-team/marp-cli markdown/deck.md --images png -o slides/deck.png
# → slides/deck.001.png, deck.002.png, ... (1 スライド 1 PNG)
```

注意点:
- `--images png` (複数形)。`-o` の拡張子は `.png` が必須
- Chrome が見つからない場合 / サンドボックス制約下では:
  `CHROME_PATH=/path/to/chrome-headless-shell CHROME_NO_SANDBOX=true npx --yes @marp-team/marp-cli ...`

### 1. ナレーション台本を書く — LLM プロンプト例

スライド 1 枚 = ナレーション 1 ブロックの 1:1 対応で作ります。
台本は 2 種類、**同じ本文から**作るのが運用上安全です (音声だけ / 動画用)。

プロンプト例 (コンテンツを渡して生成させる):

```
このスライド内容の日本語ナレーション台本を書いて。条件:
- スライド 1 枚につき 1 ブロック (全部で N ブロック)
- 略語は初出時に正式名称に展開して読み上げる (例: WSI → 「全スライド画像」)
- 表や箇条書きはそのまま読まず、意味が伝わる散文にする
- 数字は聞き取りやすい形に (例: 122,191 → 「約12万2千」ではなく正確に読むなら「12万2191」)
- 英語由来の用語は「翻訳した内容 (英語表記)」の順で一度だけ言う
- セクションの切り替わりに 1〜2 秒の無音を入れる余地を残す
```

**音声用スクリプト** (`demo/audio_scripts/narration.txt` 形式):
プレーンテキスト。セクション区切りは独行の `[[PAUSE 1.0]]` / `[[PAUSE 1.5]]` / `[[PAUSE 2.0]]`
(この秒数だけ無音を挿入)。

**動画用スクリプト** (`demo/audio_scripts/video_script.txt` 形式):
独行の `===` でブロック区切り。ブロック n が PNG n 枚目に対応。
先頭が `#` の行はコメント (合成されない)。

### 2. TTS サーバーを起動 — Irodori-TTS-Server

```bash
git clone https://github.com/Aratako/Irodori-TTS-Server.git
cd Irodori-TTS-Server
uv sync --extra cu128     # NVIDIA CUDA 12.8 (rocm / cpu も可)
cp .env.example .env
uv run --no-sync python -m irodori_openai_tts --host 0.0.0.0 --port 8088
```

既定で Hugging Face の `Aratako/Irodori-TTS-v4-Small` を初回にダウンロードします。
声質はリクエストの `irodori.caption` (Voice Design) で指定します。参照音声なしで動きます。

### 3. 音声を合成する

```bash
# 音声だけ配信用の 1 MP3 (セクション連結、間に指定秒の無音)
python3 scripts/synthesize_audio.py demo/audio_scripts/narration.txt out/audio.mp3

# 動画用: ブロックごとに合成 → 実測尺 → timing.json
python3 scripts/build_video.py demo/audio_scripts/video_script.txt \
    "demo/slides/deck.*.png" remotion/public/demo
```

既定の音声設定: mono・64kbps MP3、caption は「落ち着いた低めの女性の声…」。
環境変数で変更できます:

| 変数 | 既定値 | 意味 |
|---|---|---|
| `IRODORI_BASE_URL` | `http://localhost:8088` | TTS サーバー URL |
| `IRODORI_MODEL` | `irodori-tts` | `/v1/audio/speech` の model フィールド |
| `IRODORI_CAPTION` | 落ち着いた女性の声 | Voice Design caption |
| `AUDIO_BITRATE` | `64k` | MP3 ビットレート |
| `VIDEO_FPS` | `30` | 動画 FPS |
| `VIDEO_GAP_SEC` | `1.2` | 音声末尾のスライド維持余白 (秒) |

### 4. `timing.json` の仕様

`build_video.py` が `remotion/public/<deck>/timing.json` を出力します:

```json
{
  "fps": 30,
  "gap_sec": 1.2,
  "scenes": [
    {
      "id": "scene_01",
      "slide": "deck.001.png",     // <deck>/slides/ 内の PNG ファイル名
      "audio": "audio/001.mp3",    // <deck>/ からの相対パス
      "duration_sec": 23.8,        // 音声の実測長
      "frames": 750                // duration_sec*fps + gap_sec*fps を丸めたもの
    }
  ]
}
```

`frames` が既に余白込みなので、Remotion 側は `frames` をそのままシーン長に使います。

### 5. Remotion でレンダリング

`remotion/` はテンプレート済み (`src/SlideShow.tsx` が timing.json に従って
音声 1 ブロック = 1 スライドを再生)。`remotion/public/<deck>/` に
`slides/`, `audio/`, `timing.json` を置く形で増やせます。

```bash
cd remotion
npm install
npm run studio              # プレビュー (Remotion Studio)
npm run render:demo         # out/demo.mp4
```

追加デッキは `src/Root.tsx` に `<Composition>` を追加し、timing.json を import して
`baseDir` を切り替えます。Chrome が見つからない環境では:

```bash
npx remotion render Demo out/demo.mp4 --browser-executable=/path/to/chrome-headless-shell
```

## デモ

```bash
cd remotion
npm install
npm run render:demo
# → out/demo.mp4 (約 2 分, 1920x1080@30fps, 4 シーン)
```

デモの音声は `demo/demo_audio.mp3` (連結 MP3) として同梱。台本は `demo/audio_scripts/` を参照。
デモのコンテンツ (4 枚の解説スライド) はこのパイプライン自体についての架空の例です。

## 免責 / 備考

- TTS 音声・スライド PNG・timing.json はすべて架空のデモデータです
- 音声合成は時間がかかります (目安: 1 ブロック約 100 字 → CPU/シングル GPU で数十秒)。
  20 分超のナレーションなら数十〜数百ブロックを想定し、間欠的に再実行できる状態にしておくと安全です
