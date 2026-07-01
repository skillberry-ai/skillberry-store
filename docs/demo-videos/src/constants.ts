// Video dimensions and frame rate
export const VIDEO_WIDTH = 1920;
export const VIDEO_HEIGHT = 1080;
export const FPS = 30;

// Design tokens — clean white with blue accent (PatternFly-inspired)
export const COLORS = {
  bg: '#FFFFFF',
  bgAlt: '#F0F4F8',
  bgDark: '#151515',
  bgDarkNav: '#212427',
  primary: '#0066CC',
  primaryLight: '#E6F2FF',
  primaryDark: '#004794',
  accent: '#73C5C5',
  success: '#3E8635',
  successLight: '#F3FAF2',
  warning: '#F0AB00',
  danger: '#C9190B',
  dangerLight: '#FCECEA',
  text: '#151515',
  textMuted: '#6A6E73',
  textOnDark: '#FFFFFF',
  textMutedOnDark: '#D2D2D2',
  border: '#D2D2D2',
  borderStrong: '#B8BBBE',
  tagBg: '#EFF5FB',
  tagText: '#004794',
  code: '#1F1F1F',
  codeBg: '#1E1E1E',
  codeGreen: '#6A9955',
  codeBlue: '#9CDCFE',
  codeYellow: '#DCDCAA',
  codeOrange: '#CE9178',
  codePurple: '#C586C0',
};

// Typography
export const FONTS = {
  sans: "'Red Hat Display', 'Segoe UI', system-ui, sans-serif",
  mono: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
};

// Segment durations in frames (at 30fps)
// Total target: ~7.5 minutes = 13,500 frames
export const SEGMENTS = {
  INTRO:           { start: 0,     dur: 270  },  // 0:00 – 0:09   (9s)
  WHAT_IS_SBS:     { start: 270,   dur: 450  },  // 0:09 – 0:24  (15s)
  INSTALL:         { start: 720,   dur: 600  },  // 0:24 – 0:44  (20s)
  CLI_INTRO:       { start: 1320,  dur: 540  },  // 0:44 – 1:02  (18s)
  CLI_IMPORT:      { start: 1860,  dur: 480  },  // 1:02 – 1:18  (16s)
  UI_HOME:         { start: 2340,  dur: 300  },  // 1:18 – 1:28  (10s)
  UI_SKILLS:       { start: 2640,  dur: 420  },  // 1:28 – 1:42  (14s)
  IMPORT_DIALOG:   { start: 3060,  dur: 540  },  // 1:42 – 2:00  (18s)
  IMPORT_RESULT:   { start: 3600,  dur: 420  },  // 2:00 – 2:14  (14s)
  SKILL_DETAIL:    { start: 4020,  dur: 420  },  // 2:14 – 2:28  (14s)
  UI_TOOLS:        { start: 4440,  dur: 480  },  // 2:28 – 2:44  (16s)
  TOOL_DETAIL:     { start: 4920,  dur: 390  },  // 2:44 – 2:57  (13s)
  TOOL_EXECUTE:    { start: 5310,  dur: 480  },  // 2:57 – 3:13  (16s)
  UI_SNIPPETS:     { start: 5790,  dur: 300  },  // 3:13 – 3:23  (10s)
  UI_VMCP:         { start: 6090,  dur: 330  },  // 3:23 – 3:34  (11s)
  UI_VNFS:         { start: 6420,  dur: 300  },  // 3:34 – 3:44  (10s)
  PLUGINS_OVERVIEW:{ start: 6720,  dur: 420  },  // 3:44 – 3:58  (14s)
  PLUGIN_EVALUATOR:{ start: 7140,  dur: 480  },  // 3:58 – 4:14  (16s)
  PLUGIN_SECURITY: { start: 7620,  dur: 480  },  // 4:14 – 4:30  (16s)
  PLUGIN_DEDUPE:   { start: 8100,  dur: 480  },  // 4:30 – 4:46  (16s)
  PLUGIN_CREATOR:  { start: 8580,  dur: 480  },  // 4:46 – 5:02  (16s)
  PLUGIN_OPTIMIZER:{ start: 9060,  dur: 480  },  // 5:02 – 5:18  (16s)
  CLI_EXECUTE_TOOL:{ start: 9540,  dur: 480  },  // 5:18 – 5:34  (16s)
  OBSERVABILITY:   { start: 10020, dur: 420  },  // 5:34 – 5:48  (14s)
  ARCHITECTURE:    { start: 10440, dur: 480  },  // 5:48 – 6:04  (16s)
  OUTRO:           { start: 10920, dur: 480  },  // 6:04 – 6:20  (16s)
};

export const TOTAL_FRAMES = 11400; // ~6:20 at 30fps
