#!/usr/bin/env python3
"""
Build pipeline for the 30-second silent Skillberry teaser reel.
No TTS, no captions, no audio — the deliverable is a GIF.

Run from docs/demo-videos/skillberry-store-teaser-video/:
    python3 build.py
"""
import subprocess
from pathlib import Path

HERE        = Path(__file__).parent.resolve()
VIDEOS_ROOT = HERE.parent                       # docs/demo-videos/
OUT         = HERE / "out"
OUT.mkdir(exist_ok=True)

MP4     = OUT / "skillberry-teaser.mp4"
GIF     = OUT / "skillberry-teaser.gif"
PALETTE = OUT / "palette.png"

GIF_WIDTH = 960
GIF_FPS   = 15


def render_mp4():
    print("Step 1  Rendering Remotion MP4 ...")
    raw = OUT / "skillberry-teaser.raw.mp4"
    subprocess.check_call([
        "npx", "remotion", "render",
        "--config=remotion.shorts.config.ts",
        "SkillberryTeaser", str(raw),
    ], cwd=str(VIDEOS_ROOT))
    # Remotion emits a silent AAC track by default; strip it so the file is
    # truly audio-free (the deliverable is a GIF, and the spec requires no audio).
    print("  Stripping audio track ...")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
        "-c:v", "copy", "-an", str(MP4),
    ])
    raw.unlink(missing_ok=True)
    print(f"  -> {MP4}")


def make_gif():
    print("\nStep 2  Generating palette ...")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(MP4),
        "-vf", f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(PALETTE),
    ])
    print("Step 3  Encoding GIF with palette ...")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(MP4), "-i", str(PALETTE),
        "-lavfi", f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3",
        "-loop", "0", str(GIF),
    ])
    PALETTE.unlink(missing_ok=True)
    print(f"  -> {GIF}  ({GIF.stat().st_size/1e6:.2f} MB)")


if __name__ == "__main__":
    print("\n=== Skillberry Teaser — Build Pipeline ===\n")
    render_mp4()
    make_gif()
    print("\nDone.")
