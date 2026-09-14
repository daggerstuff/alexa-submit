import React from "react";
import { Composition } from "remotion";
import { DemoVideo, TOTAL_SECONDS } from "./DemoVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="DemoVideo"
      component={DemoVideo}
      durationInFrames={Math.ceil(TOTAL_SECONDS * 30) + 60}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};