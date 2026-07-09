// Teaser video — 30 seconds, 900 frames at 30fps. Silent, no captions.
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

//  6 scenes — durations sum to exactly 900 frames (30.00 s)
export const SEGMENTS = {
  INTRO:   { start:   0, dur: 108 },  // 0:00 – 3.6s
  IMPORT:  { start: 108, dur: 168 },  // 3.6s – 9.2s
  SCORING: { start: 276, dur: 168 },  // 9.2s – 14.8s
  EXECUTE: { start: 444, dur: 150 },  // 14.8s – 19.8s
  POWER:   { start: 594, dur: 150 },  // 19.8s – 24.8s
  OUTRO:   { start: 744, dur: 156 },  // 24.8s – 30.0s
};

export const TOTAL_FRAMES = 900;
