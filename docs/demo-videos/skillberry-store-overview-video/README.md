# Skillberry Store — Demo Video

A **~6:20** Remotion-based demo video showcasing the full Skillberry Store feature set.

## Structure

```
demo-video/
├── src/
│   ├── index.ts          # Remotion entry point
│   ├── composition.tsx   # Root <Composition> — stitches all scenes via <Series>
│   ├── constants.ts      # VIDEO_WIDTH, FPS, COLORS, SEGMENTS timing map
│   ├── components.tsx    # Reusable components (ScoreBadge, PluginCard, TerminalWindow, …)
│   ├── scenes1.tsx       # Scene 01–03: Intro, What Is SBS, Installation
│   ├── scenes2.tsx       # Scene 04–06: CLI Intro, CLI Import, UI Home
│   ├── scenes3.tsx       # Scene 07–10: UI Skills, Import Dialog, Import Result, Skill Detail
│   ├── scenes4.tsx       # Scene 11–16: Tools, Tool Detail, Execute, Snippets, VMCP, vNFS
│   ├── scenes5.tsx       # Scene 17–22: Plugins Overview + Evaluator/Security/Dedupe/Creator/Optimizer
│   └── scenes6.tsx       # Scene 23–26: CLI Execute, Observability, Architecture, Outro
├── public/
│   └── screenshots/      # 20 x 1920×1080 PNGs from the live running instance
├── VOICEOVER_SCRIPT.md   # Full narration script with timecodes (26 segments)
├── captions.srt          # SRT subtitle file (51 caption blocks)
└── package.json
```

## Scenes / Timecodes

| # | Scene | Start | Duration |
|---|-------|-------|----------|
| 01 | Intro | 0:00 | 9s |
| 02 | What is SBS | 0:09 | 15s |
| 03 | Installation | 0:24 | 20s |
| 04 | CLI Intro | 0:44 | 18s |
| 05 | CLI Import Anthropic Skill | 1:02 | 16s |
| 06 | UI Home Dashboard | 1:18 | 10s |
| 07 | UI Skills Library | 1:28 | 14s |
| 08 | Import Dialog (3 sources) | 1:42 | 18s |
| 09 | Import Result — pptx detail | 2:00 | 14s |
| 10 | Skill Detail — summarizer | 2:14 | 14s |
| 11 | Tools Registry | 2:28 | 16s |
| 12 | Tool Detail | 2:44 | 13s |
| 13 | Tool Execute (UI + CLI) | 2:57 | 16s |
| 14 | Snippets | 3:13 | 10s |
| 15 | Virtual MCP Servers | 3:23 | 11s |
| 16 | Virtual NFS Servers | 3:34 | 10s |
| 17 | Plugins Overview | 3:44 | 14s |
| 18 | Plugin: Content Evaluator | 3:58 | 16s |
| 19 | Plugin: Security Evaluator | 4:14 | 16s |
| 20 | Plugin: Skill Deduplicator | 4:30 | 16s |
| 21 | Plugin: Snippet Creator | 4:46 | 16s |
| 22 | Plugin: Skill Optimizer | 5:02 | 16s |
| 23 | CLI Execute Tool | 5:18 | 16s |
| 24 | Observability | 5:34 | 14s |
| 25 | Architecture Overview | 5:48 | 16s |
| 26 | Outro | 6:04 | 16s |

## Quick Start

```bash
cd demo-video
npm install

# Open in Remotion Studio (interactive preview)
npm run start

# Render to MP4 (requires Chrome/Chromium and ffmpeg)
mkdir -p out
npx remotion render SkillberryDemo out/skillberry-demo.mp4
```

## Prerequisites for render

- **Node.js 18+** (already installed)
- **Chrome or Chromium** — `npx remotion install chrome` or use system Chrome
- **ffmpeg** — `apt install ffmpeg` / `brew install ffmpeg`

## Voiceover

See [`VOICEOVER_SCRIPT.md`](./VOICEOVER_SCRIPT.md) for the full script with timecodes.  
Record narration against those timecodes and burn in [`captions.srt`](./captions.srt) with:

```bash
ffmpeg -i skillberry-demo.mp4 \
  -vf "subtitles=captions.srt:force_style='FontSize=22,PrimaryColour=&Hffffff,BackColour=&H80000000'" \
  -c:a copy \
  skillberry-demo-captioned.mp4
```

To add an audio track after recording:

```bash
ffmpeg -i skillberry-demo.mp4 -i voiceover.mp3 \
  -c:v copy -c:a aac -shortest \
  skillberry-demo-with-audio.mp4
```

## Design

- **Resolution:** 1920 × 1080 (Full HD)
- **Frame rate:** 30 fps
- **Font:** Segoe UI / system-ui (clean white, no external font dependency)
- **Color palette:** PatternFly-inspired — `#FFFFFF` bg, `#0066CC` primary, `#151515` text
- **Style:** Clean, minimal, professional — no animations, no gradients on backgrounds
