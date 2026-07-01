#!/usr/bin/env python3
"""
Skillberry Store demo video full build pipeline:
  1. Generate TTS voiceover (gTTS) for each of the 26 scenes
  2. Assemble into a single 380-second WAV track with correct scene offsets
  3. Render the Remotion composition to a silent MP4
  4. Merge audio + video with ffmpeg
  5. Burn captions.srt into the final MP4

Run from the docs/demo-video directory:
    python3 build.py
"""

import subprocess, sys, os, struct, wave, tempfile
from pathlib import Path

# ── ensure gtts is available ────────────────────────────────────────────────
try:
    from gtts import gTTS
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gtts", "-q"])
    from gtts import gTTS

HERE = Path(__file__).parent.resolve()
OUT  = HERE / "out"
TMP  = HERE / "out" / "tts_segments"
OUT.mkdir(exist_ok=True)
TMP.mkdir(exist_ok=True)

FPS         = 30
TOTAL_SEC   = 380          # 11 400 frames / 30 fps
SAMPLE_RATE = 44100

# ── Scene definitions: (name, start_frame, voiceover_text) ─────────────────
# Timings from constants.ts SEGMENTS map.
SCENES = [
    (  "01_intro",
       0,
       "Welcome to Skillberry Store. A smart skills repository built for agentic workflows."
    ),
    (  "02_what_is",
       270,
       "Skillberry Store is a central place to manage every tool your AI agents need. "
       "Upload once, execute anywhere, and manage everything from a single service. "
       "It handles tools, skills, and snippets, with semantic search, lifecycle management, "
       "virtual M C P servers, and a rich plugin ecosystem."
    ),
    (  "03_install",
       720,
       "Installation is straightforward. You can install just the core service with pip, "
       "or bundle in the AI plugins in one command. To run with Docker, a single make command "
       "starts everything. After a few seconds, the web UI is live on port 8002, "
       "the REST API on 8000, and the M C P control endpoint is ready for any AI client."
    ),
    (  "04_cli_intro",
       1320,
       "Skillberry Store includes an auto-generated command-line interface called S B S. "
       "It's built on top of restish and mirrors every single REST endpoint. "
       "Install the S D K, run sbs connect to point it at your server, and every operation — "
       "skills, tools, snippets, virtual M C P and N F S servers, plus all admin commands — "
       "is available at your fingertips."
    ),
    (  "05_cli_import",
       1860,
       "Let's import our first skill. Skillberry supports three import paths: a GitHub URL, "
       "a zip file, or a local folder path. Here we use curl against the import Anthropic endpoint, "
       "pointing it at the P P T X skill on disk. The response confirms the skill was created "
       "with sixty-six tools and forty-three snippets, in a single call."
    ),
    (  "06_ui_home",
       2340,
       "The web UI launches automatically alongside the backend. From the dashboard you can navigate "
       "to Skills, Tools, Snippets, virtual M C P and N F S servers, Plugins, Observability, "
       "and the Admin panel."
    ),
    (  "07_ui_skills",
       2640,
       "Here's the Skills library with our two imported skills — the P P T X skill with sixty-six tools, "
       "and the Summarizer with twenty-nine. Notice the auto-applied tags: anthropic, imported, "
       "quality score, performance score, and security score. Those were generated automatically "
       "by the Evaluator and Security plugins on import."
    ),
    (  "08_import_dialog",
       3060,
       "Let's walk through the import dialog in the UI. Click Import Anthropic Skill on the Skills page "
       "and you get three source options. GitHub URL for pointing directly at any Anthropic skills "
       "repository. Zip file for uploading an archive — perfect for air-gapped environments. "
       "And local folder for providing an absolute path on the server — ideal for CI/CD pipelines. "
       "One click and the entire skill tree, tools, snippets, and all documentation is imported."
    ),
    (  "09_import_result",
       3600,
       "Here's the P P T X skill detail page after import. Sixty-six tools are listed as clickable tags, "
       "along with forty-three snippets. The description, tags, version, and last-modified timestamp "
       "are all tracked. You can export back to the Anthropic format, edit metadata, or delete the skill "
       "— with a cascade option to clean up all associated tools and snippets."
    ),
    (  "10_skill_detail",
       4020,
       "Here's the Summarizer skill. Twenty-nine tools, two snippets — one of which is the full "
       "README documentation. The evaluator has already scored it nine out of ten for quality, "
       "eight for performance, and eight for security. Those scores are immediately searchable "
       "and filterable across the whole library."
    ),
    (  "11_ui_tools",
       4440,
       "The Tools page shows all ninety-five tools from both skills in one table. You can sort by any column, "
       "filter by tags, switch between text and semantic search, and select multiple tools for bulk "
       "export or deletion. Each row shows the tool name, description, state, all its tags, "
       "the module file name, and version."
    ),
    (  "12_tool_detail",
       4920,
       "Clicking a tool opens its detail page. Here we have create bullet summary from the Summarizer skill. "
       "We can see its programming language, packaging format, the full dependency graph, "
       "and the JSON parameter schema. There's also a Source Code tab showing the raw Python module."
    ),
    (  "13_tool_execute",
       5310,
       "To execute a tool, hit the Execute button. A dialog accepts the parameters as JSON, "
       "and when you confirm, the tool runs inside a Docker sandbox — completely isolated from the host. "
       "You get the result back as structured JSON. From the CLI, it's one sbs execute-tool command "
       "with a body flag. Same Docker sandbox, same isolation, scriptable for automation."
    ),
    (  "14_ui_snippets",
       5790,
       "Snippets are code fragments and documentation files imported alongside the tools. "
       "They're stored with syntax highlighting and searchable by content or tags — perfect for "
       "reference material, configuration templates, or shared utility code that tools depend on."
    ),
    (  "15_vmcp",
       6090,
       "Virtual M C P Servers let you expose any subset of tools as a standalone M C P endpoint. "
       "Create one from any skill, and it gets its own dedicated port and S S E URL. "
       "Point Claude, Cursor, or any M C P-compatible client at that URL and it instantly sees "
       "only the tools from that skill — clean, scoped, and independent."
    ),
    (  "16_vnfs",
       6420,
       "Virtual N F S Servers go one step further — they expose an entire skill as a mountable, "
       "read-only filesystem over WebDAV or N F S version 3. Claude Code, rclone, or any "
       "filesystem-aware tool can mount and browse skill files directly, without going through "
       "the REST API at all."
    ),
    (  "17_plugins_overview",
       6720,
       "The Plugins page shows all installed extensions. Each plugin card displays its name, "
       "status — enabled or disabled — a description, and any action buttons. "
       "You can enable or disable individual plugins independently. "
       "Let's walk through the five most important ones."
    ),
    (  "18_plugin_evaluator",
       7140,
       "The Content Evaluator uses an L L M to analyse your skills and tools, then automatically "
       "tags them with numeric scores for quality, performance, and security. "
       "Here you can see the Summarizer skill scored nine out of ten for quality, "
       "eight for performance, and eight for security. Each score comes with a detailed written "
       "evaluation you can read in the skill's metadata. The scoring runs automatically on import, "
       "and you can re-trigger it at any time from the Plugins panel."
    ),
    (  "19_plugin_security",
       7620,
       "The Security Evaluator is a dedicated security-focused plugin. It reviews each skill for "
       "vulnerabilities — input validation gaps, path-traversal risks, injection vectors, "
       "missing authentication, and known C V E exposure. The P P T X skill scored four out of ten "
       "because it accepts arbitrary file paths with no validation or sandboxing. "
       "That's immediately visible as a security score of four tag, so you know before you deploy it "
       "in a production agent. A companion S A S T scanner using Bandit is also available."
    ),
    (  "20_plugin_dedupe",
       8100,
       "The Skill Deduplicator keeps your library clean. It uses L L M-based semantic comparison — "
       "not just name matching — to find near-identical skills. When a duplicate pair is found, "
       "it creates a notification in the UI with a Keep Both or Delete Duplicate decision. "
       "The decision management API lets you automate this in CI pipelines. "
       "The detected duplicates are also tagged so you can filter and review them at any time."
    ),
    (  "21_plugin_creator",
       8580,
       "The Snippet Creator plugin lets you generate code from a natural language description. "
       "Describe what you want — for example, a Python function that converts a list of dictionaries "
       "to a Markdown table — and the L L M generates production-ready code, automatically infers "
       "the language and tags, and saves the result directly to the store. No copy-paste required. "
       "The L L M backend is configurable: OpenAI, IBM WatsonX, or any LiteLLM-compatible provider."
    ),
    (  "22_plugin_optimizer",
       9060,
       "The Skill Optimizer is the most powerful plugin. It exports a skill to a temporary directory, "
       "launches a Claude Code session inside a RunSpace container, applies optimizations — "
       "improving descriptions, fixing edge cases, adding type hints, consolidating tools — "
       "and then imports the result as a new skill named with an optimized suffix. "
       "The optimization rationale, list of changes, and source skill UUID are all saved as metadata. "
       "Re-running is always safe and idempotent."
    ),
    (  "23_cli_execute",
       9540,
       "Back to the CLI for a quick demonstration of tool execution. "
       "First, use sbs search-tools to find the right tool with a natural language query. "
       "Then run sbs execute-tool with the tool name and a JSON body. "
       "The result comes back as structured data you can pipe into jq, write to a file, "
       "or integrate into any shell script or CI pipeline."
    ),
    (  "24_observability",
       10020,
       "Skillberry Store has built-in observability. The Observability page in the UI shows "
       "a live time-series chart with tabs for Skills Metrics, Tools Metrics, Snippets Metrics, "
       "Virtual M C P Metrics, and System Metrics. On the backend, Prometheus metrics are available "
       "on port 8090 and OpenTelemetry traces go to Jaeger. "
       "Drop a Grafana dashboard on top and you have full production monitoring."
    ),
    (  "25_architecture",
       10440,
       "The architecture is layered and pluggable. At the top, the Web UI and REST API. "
       "Alongside those, the M C P frontend and Virtual N F S servers. "
       "In the middle, the core data model — skills, tools, and snippets. "
       "Below that, Docker-sandboxed tool execution, pluggable storage backends — "
       "filesystem or GitHub — and the AI plugin layer. "
       "Everything is observable, versioned, and extensible."
    ),
    (  "26_outro",
       10920,
       "That's Skillberry Store. One service for managing, executing, and organizing every skill "
       "your AI agents need. Install with pip, start with make docker-run, "
       "and you're live in under a minute. "
       "The repository is at github dot com slash skillberry-ai slash skillberry-store. "
       "Give it a try."
    ),
]


def frames_to_sec(frames: int) -> float:
    return frames / FPS


def sec_to_samples(sec: float, rate: int = SAMPLE_RATE) -> int:
    return int(sec * rate)


def mp3_to_wav(mp3_path: Path, wav_path: Path) -> None:
    subprocess.check_call(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3_path), str(wav_path)],
    )


def get_wav_duration(wav_path: Path) -> float:
    with wave.open(str(wav_path)) as wf:
        return wf.getnframes() / wf.getframerate()


def read_wav_samples(wav_path: Path) -> tuple[int, int, bytes]:
    """Return (sample_rate, n_channels, raw_pcm_bytes) resampled to SAMPLE_RATE mono."""
    # Resample + mono via ffmpeg to a temp file
    tmp = wav_path.with_suffix(".pcm.wav")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(wav_path),
        "-ar", str(SAMPLE_RATE), "-ac", "1",
        str(tmp),
    ])
    with wave.open(str(tmp)) as wf:
        data = wf.readframes(wf.getnframes())
    tmp.unlink(missing_ok=True)
    return data


def write_silence(n_samples: int) -> bytes:
    return b"\x00\x00" * n_samples   # 16-bit little-endian zeros


def build_voiceover() -> Path:
    """Generate per-scene MP3s, assemble into a single WAV at correct offsets."""
    total_samples = sec_to_samples(TOTAL_SEC)
    # Pre-allocate silence buffer (16-bit mono)
    buf = bytearray(total_samples * 2)

    for name, start_frame, text in SCENES:
        mp3 = TMP / f"{name}.mp3"
        wav = TMP / f"{name}.wav"

        if not mp3.exists():
            print(f"  TTS → {name} ...", end=" ", flush=True)
            gTTS(text=text, lang="en", slow=False).save(str(mp3))
            print("done")
        else:
            print(f"  TTS → {name} (cached)")

        mp3_to_wav(mp3, wav)
        pcm = read_wav_samples(wav)

        start_sample = sec_to_samples(frames_to_sec(start_frame))
        byte_offset   = start_sample * 2          # 16-bit = 2 bytes/sample
        end_byte      = byte_offset + len(pcm)

        if end_byte > len(buf):
            end_byte = len(buf)
            pcm = pcm[: end_byte - byte_offset]

        buf[byte_offset:end_byte] = pcm

    # Write WAV
    out_wav = OUT / "voiceover.wav"
    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)        # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(buf))

    # Convert to MP3 for convenience
    out_mp3 = OUT / "voiceover.mp3"
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(out_wav),
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        str(out_mp3),
    ])
    print(f"  Voiceover → {out_wav}  ({TOTAL_SEC}s)")
    return out_wav


def render_video() -> Path:
    """Run Remotion render to produce the silent MP4."""
    silent_mp4 = OUT / "skillberry-demo-silent.mp4"
    if silent_mp4.exists():
        print(f"  Silent MP4 already exists, skipping render.")
        return silent_mp4

    print("  Rendering Remotion composition (this takes a few minutes) ...")
    subprocess.check_call([
        "npx", "remotion", "render",
        "SkillberryDemo",
        str(silent_mp4),
        "--log=verbose",
    ], cwd=str(HERE))
    print(f"  Silent MP4 → {silent_mp4}")
    return silent_mp4


def merge_and_caption(silent_mp4: Path, voiceover_wav: Path) -> Path:
    """Merge audio into video, then burn captions."""
    merged_mp4   = OUT / "skillberry-demo-with-audio.mp4"
    captioned_mp4 = OUT / "skillberry-demo-final.mp4"
    srt          = HERE / "captions.srt"

    # 1. Merge audio
    print("  Merging audio into video ...")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(silent_mp4),
        "-i", str(voiceover_wav),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(merged_mp4),
    ])

    # 2. Burn captions
    print("  Burning captions ...")
    srt_escaped = str(srt).replace(":", "\\:")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(merged_mp4),
        "-vf", (
            f"subtitles={srt_escaped}"
            ":force_style='FontName=Arial,FontSize=22,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=2,"
            "Shadow=1,Alignment=2,MarginV=40'"
        ),
        "-c:a", "copy",
        str(captioned_mp4),
    ])
    print(f"\n  ✅  Final video → {captioned_mp4}")
    return captioned_mp4


def main():
    print("\n═══ Skillberry Store Demo — Build Pipeline ═══\n")

    print("Step 1/3  Generating voiceover audio ...")
    voiceover = build_voiceover()

    print("\nStep 2/3  Rendering Remotion video ...")
    silent = render_video()

    print("\nStep 3/3  Merging audio + burning captions ...")
    final = merge_and_caption(silent, voiceover)

    size_mb = final.stat().st_size / 1_048_576
    print(f"\n  Size: {size_mb:.1f} MB")
    print("  Done! 🎉\n")


if __name__ == "__main__":
    main()
