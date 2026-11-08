import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile } from "remotion";

export type Scene = {
  id: string;
  slide: string;
  audio: string;
  duration_sec: number;
  frames: number;
};

export type Timing = {
  fps: number;
  gap_sec: number;
  scenes: Scene[];
};

// 1ブロック音声 = 1スライド。音声末尾に gap_sec 分の余白（次のスライドへ進むまでの無音）を
// 含んだ frames を各シーンの長さに使う (build_video.py が frames に織り込む)。
export const SlideShow: React.FC<{ timing: Timing; baseDir: string }> = ({
  timing,
  baseDir,
}) => {
  let from = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "white" }}>
      {timing.scenes.map((s) => {
        const start = from;
        from += s.frames;
        return (
          <Sequence
            key={s.id}
            from={start}
            durationInFrames={s.frames}
            name={s.id}
          >
            <Img
              src={staticFile(`${baseDir}/slides/${s.slide}`)}
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
            <Audio src={staticFile(`${baseDir}/${s.audio}`)} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
