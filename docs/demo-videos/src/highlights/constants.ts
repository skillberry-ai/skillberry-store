// Highlights video — 65 seconds, 1950 frames at 30fps
export const VIDEO_WIDTH  = 1920;
export const VIDEO_HEIGHT = 1080;
export const FPS          = 30;

export const COLORS = {
  bg:           '#FFFFFF',
  bgAlt:        '#F0F4F8',
  primary:      '#0066CC',
  primaryLight: '#E6F2FF',
  accent:       '#73C5C5',
  success:      '#3E8635',
  successLight: '#F3FAF2',
  warning:      '#F0AB00',
  danger:       '#C9190B',
  dangerLight:  '#FCECEA',
  text:         '#151515',
  textMuted:    '#6A6E73',
  border:       '#D2D2D2',
  tagBg:        '#EFF5FB',
  tagText:      '#004794',
  codeBg:       '#1E1E1E',
  codeGreen:    '#6A9955',
};

//  9 scenes — slots widened so TTS audio at 1.8× never gets truncated
//  Total: 1950 frames = 65.00 s
export const SEGMENTS = {
  INTRO:          { start:    0, dur: 150 },  // 0:00 – 0:05   (5s)
  INSTALL:        { start:  150, dur: 210 },  // 0:05 – 0:12   (7s)  was 6s — truncated
  IMPORT_SKILL:   { start:  360, dur: 240 },  // 0:12 – 0:20   (8s)  was 7s — truncated
  SKILLS_UI:      { start:  600, dur: 210 },  // 0:20 – 0:27   (7s)
  EXECUTE_TOOL:   { start:  810, dur: 240 },  // 0:27 – 0:35   (8s)  was 7s — truncated
  PLUGIN_EVAL:    { start: 1050, dur: 210 },  // 0:35 – 0:42   (7s)
  PLUGIN_SEC:     { start: 1260, dur: 210 },  // 0:42 – 0:49   (7s)  was 6s — truncated
  VMCP:           { start: 1470, dur: 210 },  // 0:49 – 0:56   (7s)  was 6s — truncated
  OUTRO:          { start: 1680, dur: 270 },  // 0:56 – 1:05   (9s)
};

export const TOTAL_FRAMES = 1950;
