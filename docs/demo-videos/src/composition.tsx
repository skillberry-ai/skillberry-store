import React from 'react';
import { Composition, Series, AbsoluteFill } from 'remotion';
import { VIDEO_WIDTH, VIDEO_HEIGHT, FPS, TOTAL_FRAMES, SEGMENTS } from './constants';

// Import all scenes
import { SceneIntro, SceneWhatIs, SceneInstall } from './scenes1';
import { SceneCLIIntro, SceneCLIImport, SceneUIHome } from './scenes2';
import { SceneUISkills, SceneImportDialog, SceneImportResult, SceneSkillDetail } from './scenes3';
import { SceneUITools, SceneToolDetail, SceneToolExecute, SceneUISnippets, SceneVMCP, SceneVNFS } from './scenes4';
import { ScenePluginsOverview, ScenePluginEvaluator, ScenePluginSecurity, ScenePluginDedupe, ScenePluginCreator, ScenePluginOptimizer } from './scenes5';
import { SceneCLIExecuteTool, SceneObservability, SceneArchitecture, SceneOutro } from './scenes6';

// The full demo — all scenes stitched via <Series>
const SkillberryDemo: React.FC = () => (
  <AbsoluteFill>
    <Series>
      <Series.Sequence durationInFrames={SEGMENTS.INTRO.dur}>
        <SceneIntro />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.WHAT_IS_SBS.dur}>
        <SceneWhatIs />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.INSTALL.dur}>
        <SceneInstall />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.CLI_INTRO.dur}>
        <SceneCLIIntro />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.CLI_IMPORT.dur}>
        <SceneCLIImport />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.UI_HOME.dur}>
        <SceneUIHome />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.UI_SKILLS.dur}>
        <SceneUISkills />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.IMPORT_DIALOG.dur}>
        <SceneImportDialog />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.IMPORT_RESULT.dur}>
        <SceneImportResult />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.SKILL_DETAIL.dur}>
        <SceneSkillDetail />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.UI_TOOLS.dur}>
        <SceneUITools />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.TOOL_DETAIL.dur}>
        <SceneToolDetail />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.TOOL_EXECUTE.dur}>
        <SceneToolExecute />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.UI_SNIPPETS.dur}>
        <SceneUISnippets />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.UI_VMCP.dur}>
        <SceneVMCP />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.UI_VNFS.dur}>
        <SceneVNFS />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.PLUGINS_OVERVIEW.dur}>
        <ScenePluginsOverview />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.PLUGIN_EVALUATOR.dur}>
        <ScenePluginEvaluator />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.PLUGIN_SECURITY.dur}>
        <ScenePluginSecurity />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.PLUGIN_DEDUPE.dur}>
        <ScenePluginDedupe />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.PLUGIN_CREATOR.dur}>
        <ScenePluginCreator />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.PLUGIN_OPTIMIZER.dur}>
        <ScenePluginOptimizer />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.CLI_EXECUTE_TOOL.dur}>
        <SceneCLIExecuteTool />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.OBSERVABILITY.dur}>
        <SceneObservability />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.ARCHITECTURE.dur}>
        <SceneArchitecture />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SEGMENTS.OUTRO.dur}>
        <SceneOutro />
      </Series.Sequence>
    </Series>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="SkillberryDemo"
      component={SkillberryDemo}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      defaultProps={{}}
    />
  </>
);
