import React from "react";
import { Composition } from "remotion";
import demoTiming from "../public/demo/timing.json";
import { SlideShow, type Timing } from "./SlideShow";

const totalFrames = (t: Timing) =>
  t.scenes.reduce((acc, s) => acc + s.frames, 0);

// 追加動画は <Composition> を増やし、timing.json を import して baseDir を切り替える。
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Demo"
        component={SlideShow}
        durationInFrames={totalFrames(demoTiming as Timing)}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ timing: demoTiming as Timing, baseDir: "demo" }}
      />
    </>
  );
};
