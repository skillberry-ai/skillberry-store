import React from 'react';
import { Composition, Series, AbsoluteFill } from 'remotion';
import { VIDEO_WIDTH, VIDEO_HEIGHT, FPS, TOTAL_FRAMES, SEGMENTS } from './constants';
import {
  HlIntro, HlInstall, HlImport, HlSkillsUI,
  HlExecute, HlPluginEval, HlPluginSec, HlVMCP, HlOutro,
} from './scenes';

const SkillberryHighlights: React.FC = () => (
  <AbsoluteFill>
    <Series>
      <Series.Sequence durationInFrames={SEGMENTS.INTRO.dur}>        <HlIntro />      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.INSTALL.dur}>      <HlInstall />    </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.IMPORT_SKILL.dur}> <HlImport />     </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.SKILLS_UI.dur}>    <HlSkillsUI />   </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.EXECUTE_TOOL.dur}> <HlExecute />    </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.PLUGIN_EVAL.dur}>  <HlPluginEval /> </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.PLUGIN_SEC.dur}>   <HlPluginSec />  </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.VMCP.dur}>         <HlVMCP />       </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.OUTRO.dur}>        <HlOutro />      </Series.Sequence>
    </Series>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="SkillberryHighlights"
      component={SkillberryHighlights}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      defaultProps={{}}
    />
  </>
);
