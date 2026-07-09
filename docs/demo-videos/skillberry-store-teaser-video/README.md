# Skillberry Store — 30-Second Teaser

A **30s**, silent, subtitle-free Remotion reel showcasing the most impressive
Skillberry Store features. Intended as the README hero GIF for newcomers.

## Structure

Shares the parent `docs/demo-videos/` Remotion project and its
`public/screenshots/`. Teaser-specific code lives in:

```
src/
├── shorts-index.ts        # Remotion entry point
└── shorts/
    ├── constants.ts       # 900-frame, 6-segment timing map + palette
    ├── composition.tsx    # <Composition id="SkillberryTeaser"> — 6 scenes via <Series>
    └── scenes.tsx         # 6 silent-timed scenes + inline SVG icons
remotion.shorts.config.ts  # sets the shorts entry point
```

## Scenes (900 frames / 30s @ 30fps)

| # | Scene | Dur | Content |
|---|-------|-----|---------|
| 1 | Intro | 3.6s | Logo + "Skillberry Store" + tagline |
| 2 | Import | 5.6s | 3 import sources → 66 tools + 43 snippets in one click |
| 3 | AI Scoring | 5.6s | Content Evaluator + Security Scanner + score bars (9/8/8) |
| 4 | Execute | 5.0s | Tool run in a Docker sandbox (UI + CLI) |
| 5 | Power features | 5.0s | Virtual MCP · Virtual NFS · Observability |
| 6 | Outro | 5.2s | Install/run chips + GitHub URL |

## Build

```bash
# from docs/demo-videos/
npm install                 # once
npm run start-teaser        # interactive Remotion Studio preview

# from docs/demo-videos/skillberry-store-teaser-video/
python3 build.py            # renders out/skillberry-teaser.mp4 + out/skillberry-teaser.gif
```

## Prerequisites

- Node.js 18+
- Chrome/Chromium — `npx remotion browser ensure`
- ffmpeg — `apt install ffmpeg` / `brew install ffmpeg`

## Design

- 1920×1080, 30 fps, **silent** (no audio, no captions). The build strips the
  silent audio track Remotion emits by default.
- PatternFly-inspired palette, reuses real UI screenshots, inline SVG icons
  (headless Chromium has no color-emoji font).
- The GIF is produced via two-pass ffmpeg palette (960px wide, 15 fps) for a
  small, README-friendly file.
