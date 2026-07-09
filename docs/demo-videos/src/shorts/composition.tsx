import React from 'react';
import { Composition, Series, AbsoluteFill } from 'remotion';
import { VIDEO_WIDTH, VIDEO_HEIGHT, FPS, TOTAL_FRAMES, SEGMENTS } from './constants';
import { TzIntro, TzImport, TzScoring, TzExecute, TzPower, TzOutro } from './scenes';

const SkillberryTeaser: React.FC = () => (
  <AbsoluteFill>
    <Series>
      <Series.Sequence durationInFrames={SEGMENTS.INTRO.dur}>   <TzIntro />   </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.IMPORT.dur}>  <TzImport />  </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.SCORING.dur}> <TzScoring /> </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.EXECUTE.dur}> <TzExecute /> </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.POWER.dur}>   <TzPower />   </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.OUTRO.dur}>   <TzOutro />   </Series.Sequence>
    </Series>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <Composition
    id="SkillberryTeaser"
    component={SkillberryTeaser}
    durationInFrames={TOTAL_FRAMES}
    fps={FPS}
    width={VIDEO_WIDTH}
    height={VIDEO_HEIGHT}
    defaultProps={{}}
  />
);
