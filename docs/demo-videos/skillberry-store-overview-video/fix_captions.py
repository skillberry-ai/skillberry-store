#!/usr/bin/env python3
"""
Generate a precise captions.srt from the actual TTS audio timing.

For each scene:
  1. Detect the actual speech start/end within its slot (strip leading/trailing silence)
  2. Split the spoken text into caption lines (max ~60 chars, ~4 words/line)
  3. Distribute those lines evenly across the detected speech window
  4. Write out a properly timed .srt file

Then re-burn the captions into the final MP4.
"""
import subprocess, re, wave, struct
from pathlib import Path

HERE = Path(__file__).parent.resolve()
OUT  = HERE / "out"
TMP  = OUT / "tts_segments"
SRT  = HERE / "captions.srt"

FPS         = 30
TOTAL_SEC   = 380
SAMPLE_RATE = 44100
SILENCE_THRESHOLD = 200   # 16-bit PCM amplitude below this = silence

# Same scene list as rebuild_audio.py — name, start_frame, slot_sec, spoken text
SCENES = [
    ("01_intro", 0, 9,
     "Welcome to Skillberry Store — a smart skills repository for agentic workflows."),

    ("02_what_is", 270, 15,
     "Skillberry Store centralises every tool your AI agents need. "
     "Upload once, execute anywhere. It manages tools, skills, and snippets "
     "with semantic search, lifecycle management, virtual MCP servers, and a plugin ecosystem."),

    ("03_install", 720, 20,
     "Installation is simple. Install with pip, optionally bundle the AI plugins. "
     "Run with Docker using a single make command. "
     "The web UI starts on port 8002, the REST API on 8000, "
     "and the MCP control endpoint is ready for any AI client."),

    ("04_cli_intro", 1320, 18,
     "The auto-generated CLI is called sbs. Built on restish, it mirrors every REST endpoint. "
     "Run sbs connect to point it at your server. "
     "Skills, tools, snippets, virtual servers, and admin commands are all available."),

    ("05_cli_import", 1860, 16,
     "Let's import a skill. Three paths are supported: GitHub URL, zip file, or local folder. "
     "Here we point the API at the PPTX skill on disk. "
     "The response confirms 66 tools and 43 snippets created in one call."),

    ("06_ui_home", 2340, 10,
     "The web UI starts automatically. From the dashboard navigate to Skills, Tools, Snippets, "
     "virtual servers, Plugins, Observability, and Admin."),

    ("07_ui_skills", 2640, 14,
     "The Skills library shows our two imported skills — pptx with 66 tools, summarizer with 29. "
     "Tags like quality-score, performance-score, and security-score "
     "were auto-applied by the AI plugins on import."),

    ("08_import_dialog", 3060, 18,
     "The Import Anthropic Skill dialog offers three sources: "
     "GitHub URL, zip file for air-gapped environments, "
     "or local folder for CI/CD pipelines. "
     "One click imports the full skill tree — tools, snippets, and documentation."),

    ("09_import_result", 3600, 14,
     "Here's the pptx skill after import — 66 tools, 43 snippets, full metadata. "
     "You can export back to Anthropic format, edit metadata, "
     "or delete with a cascade option to clean up all linked objects."),

    ("10_skill_detail", 4020, 14,
     "The Summarizer skill: 29 tools, 2 snippets. "
     "The evaluator scored it 9 out of 10 for quality, 8 for performance, 8 for security. "
     "Scores are searchable and filterable across the library."),

    ("11_ui_tools", 4440, 16,
     "The Tools page shows all 95 tools in one sortable table. "
     "Filter by tags, switch between text and semantic search, "
     "and select multiple tools for bulk export or deletion."),

    ("12_tool_detail", 4920, 13,
     "Clicking a tool opens its detail page — programming language, packaging format, "
     "dependencies, and the JSON parameter schema. "
     "A Source Code tab shows the raw Python module."),

    ("13_tool_execute", 5310, 16,
     "Hit Execute to run a tool. Parameters go in as JSON, "
     "and the tool runs inside a Docker sandbox — isolated from the host. "
     "From the CLI: sbs execute-tool with a body flag. Same sandbox, scriptable."),

    ("14_ui_snippets", 5790, 10,
     "Snippets are code fragments and docs imported with the skill. "
     "Syntax-highlighted and searchable — perfect for shared utility code."),

    ("15_vmcp", 6090, 11,
     "Virtual MCP Servers expose a skill's tools as a standalone MCP endpoint. "
     "Each gets its own port and SSE URL — connect Claude, Cursor, or any MCP client directly."),

    ("16_vnfs", 6420, 10,
     "Virtual NFS Servers expose a skill as a mountable read-only filesystem "
     "over WebDAV or NFSv3 — Claude Code and rclone can read files without the REST API."),

    ("17_plugins_overview", 6720, 14,
     "The Plugins page shows all AI-powered extensions. Enable or disable each independently. "
     "Let's walk through the five key plugins."),

    ("18_plugin_evaluator", 7140, 16,
     "The Content Evaluator tags skills and tools with quality, performance, and security scores. "
     "The Summarizer scored 9 for quality, 8 for performance, 8 for security. "
     "Each score includes a written explanation. Triggered on import or on demand."),

    ("19_plugin_security", 7620, 16,
     "The Security Evaluator finds vulnerabilities — path traversal, injection, missing auth. "
     "The pptx skill scored 4 out of 10 because it accepts arbitrary file paths "
     "with no validation. Visible as a security-score tag before you deploy."),

    ("20_plugin_dedupe", 8100, 16,
     "The Skill Deduplicator uses LLM semantic comparison to find near-identical skills. "
     "When duplicates are found, a notification appears with Keep or Delete decisions. "
     "The decision API lets you automate this in CI pipelines."),

    ("21_plugin_creator", 8580, 16,
     "The Snippet Creator generates code from a natural language description. "
     "Describe what you want, the LLM writes it, infers the language and tags, "
     "and saves it to the store. No copy-paste. Works with OpenAI, WatsonX, or LiteLLM."),

    ("22_plugin_optimizer", 9060, 16,
     "The Skill Optimizer exports a skill, runs Claude Code in a RunSpace container, "
     "and imports the optimized result with an optimized suffix. "
     "Rationale and changes are saved as metadata. Safe to re-run any time."),

    ("23_cli_execute", 9540, 16,
     "From the CLI, use sbs search-tools to find the right tool, "
     "then sbs execute-tool with a JSON body. "
     "Results pipe into jq, files, or any CI pipeline. Every operation is scriptable."),

    ("24_observability", 10020, 14,
     "Built-in observability: live time-series charts for skills, tools, snippets, and system metrics. "
     "Prometheus on port 8090. Jaeger traces. Drop a Grafana dashboard on top for full monitoring."),

    ("25_architecture", 10440, 16,
     "The architecture is layered: Web UI and REST API at the top, "
     "MCP frontend and virtual NFS alongside, core data model in the middle, "
     "Docker sandbox and pluggable storage below, and the AI plugin layer at the base."),

    ("26_outro", 10920, 16,
     "That's Skillberry Store — one service for every skill your agents need. "
     "Install with pip, start with make docker-run, live in under a minute. "
     "Find us at github.com slash skillberry-ai slash skillberry-store."),
]


# ── helpers ─────────────────────────────────────────────────────────────────

def srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def get_audio_duration(mp3: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(mp3)],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def mp3_to_mono_wav(mp3: Path, wav: Path) -> None:
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(mp3),
        "-ar", str(SAMPLE_RATE), "-ac", "1",
        str(wav)])


def detect_speech_bounds(wav_path: Path, threshold: int = SILENCE_THRESHOLD) -> tuple[float, float]:
    """Return (speech_start_sec, speech_end_sec) by scanning PCM for non-silence."""
    with wave.open(str(wav_path)) as wf:
        n = wf.getnframes()
        rate = wf.getframerate()
        raw = wf.readframes(n)
    samples = struct.unpack(f"<{n}h", raw)

    # scan forward for first non-silent sample
    start_sample = 0
    for i, s in enumerate(samples):
        if abs(s) > threshold:
            start_sample = max(0, i - int(rate * 0.05))   # 50ms pre-roll
            break

    # scan backward for last non-silent sample
    end_sample = n - 1
    for i in range(n - 1, -1, -1):
        if abs(samples[i]) > threshold:
            end_sample = min(n - 1, i + int(rate * 0.05))  # 50ms post-roll
            break

    return start_sample / rate, end_sample / rate


def split_into_lines(text: str, max_chars: int = 58) -> list[str]:
    """Split text into caption lines of at most max_chars each, breaking on spaces."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def chunk_lines(lines: list[str], lines_per_caption: int = 2) -> list[str]:
    """Group lines into caption blocks of up to lines_per_caption lines."""
    return [
        "\n".join(lines[i:i + lines_per_caption])
        for i in range(0, len(lines), lines_per_caption)
    ]


# ── main ─────────────────────────────────────────────────────────────────────

def build_srt() -> None:
    blocks = []
    idx = 1

    for name, start_frame, slot_sec, text in SCENES:
        scene_start_sec = start_frame / FPS
        mp3 = TMP / f"{name}.mp3"
        wav = TMP / f"{name}_cap.wav"

        # convert to WAV for analysis
        mp3_to_mono_wav(mp3, wav)
        speech_start, speech_end = detect_speech_bounds(wav)
        wav.unlink(missing_ok=True)

        # absolute times in the full video
        abs_start = scene_start_sec + speech_start
        abs_end   = scene_start_sec + speech_end

        # split text into caption chunks
        lines   = split_into_lines(text)
        chunks  = chunk_lines(lines, lines_per_caption=2)
        n       = len(chunks)

        if n == 0:
            continue

        speech_dur = abs_end - abs_start
        chunk_dur  = speech_dur / n

        for i, chunk in enumerate(chunks):
            t_start = abs_start + i * chunk_dur
            t_end   = abs_start + (i + 1) * chunk_dur - 0.05   # tiny gap between captions
            blocks.append((idx, t_start, t_end, chunk))
            idx += 1

    # write SRT
    with open(SRT, "w", encoding="utf-8") as f:
        for num, t0, t1, text in blocks:
            f.write(f"{num}\n{srt_time(t0)} --> {srt_time(t1)}\n{text}\n\n")

    print(f"  Wrote {len(blocks)} caption blocks → {SRT}")


def reburn() -> None:
    audio_mp4  = OUT / "skillberry-demo-audio.mp4"
    final_mp4  = OUT / "skillberry-demo-final.mp4"
    srt_esc    = str(SRT).replace(":", "\\:")

    print("  Burning new captions ...")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(audio_mp4),
        "-vf", (
            f"subtitles={srt_esc}"
            ":force_style='FontName=Arial,FontSize=14,Bold=0,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H80000000,Outline=2,Shadow=1,"
            "Alignment=2,MarginV=28'"
        ),
        "-c:a", "copy",
        str(final_mp4)])
    print(f"  ✅  {final_mp4}  ({final_mp4.stat().st_size/1e6:.0f} MB)")


if __name__ == "__main__":
    print("\n═══ Rebuilding precise captions ═══\n")
    print("Step 1  Detecting speech timing and generating captions.srt ...")
    build_srt()
    print("\nStep 2  Burning captions into final MP4 ...")
    reburn()
    print()
