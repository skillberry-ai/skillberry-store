#!/usr/bin/env python3
"""
Regenerate all TTS segments with scripts sized to fit their video slot,
then reassemble the voiceover WAV, re-merge audio and re-burn captions.

Each script targets (slot_seconds - 0.5s) * 2.8 words/sec to leave a
small tail gap. gTTS at slow=False speaks ~150 wpm = 2.5 w/s average;
we aim slightly under the slot.
"""
import subprocess, sys, wave
from pathlib import Path

try:
    from gtts import gTTS
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gtts", "-q"])
    from gtts import gTTS

HERE     = Path(__file__).parent.resolve()
OUT      = HERE / "out"
TMP      = OUT / "tts_segments"
SRT      = HERE / "captions.srt"

FPS         = 30
TOTAL_SEC   = 380
SAMPLE_RATE = 44100

# ── Tight scripts: each must fit its slot. ─────────────────────────────────
# Rule of thumb: gTTS at normal speed ≈ 14–15 chars/second.
# slot_sec * 14 = max character budget (conservative).
SCENES = [
    # (name, start_frame, slot_sec, text)
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


def frames_to_sec(frames):
    return frames / FPS

def sec_to_samples(sec):
    return int(sec * SAMPLE_RATE)

def mp3_to_wav(mp3, wav):
    subprocess.check_call(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), str(wav)])

def read_wav_pcm(wav_path):
    tmp = wav_path.with_suffix(".resampled.wav")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(wav_path), "-ar", str(SAMPLE_RATE), "-ac", "1", str(tmp)])
    with wave.open(str(tmp)) as wf:
        data = wf.readframes(wf.getnframes())
    tmp.unlink(missing_ok=True)
    return data

def audio_duration(mp3):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(mp3)],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def generate_tts():
    """Generate TTS for each scene, speed up if needed to fit slot."""
    for name, start_frame, slot_sec, text in SCENES:
        mp3      = TMP / f"{name}.mp3"
        fast_mp3 = TMP / f"{name}_fast.mp3"

        # Always regenerate (scripts changed)
        print(f"  TTS → {name} ...", end=" ", flush=True)
        gTTS(text=text, lang="en", slow=False).save(str(mp3))
        dur = audio_duration(mp3)
        print(f"{dur:.1f}s / {slot_sec}s", end="")

        target = slot_sec - 0.4          # leave 0.4s tail gap
        if dur > target:
            # Speed up with atempo; cap at 1.8x to keep intelligibility
            ratio = min(dur / target, 1.8)
            print(f"  → speeding up {ratio:.2f}x", end="")
            subprocess.check_call([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(mp3),
                "-af", f"atempo={ratio:.4f}",
                str(fast_mp3)], )
            fast_dur = audio_duration(fast_mp3)
            print(f"  → {fast_dur:.1f}s", end="")
            if fast_dur <= target + 0.1:
                fast_mp3.rename(mp3)
            else:
                # Still too long even at 1.8x — truncate to fit
                print(f"  → truncating", end="")
                tmp_mp3 = TMP / f"{name}_trunc.mp3"
                subprocess.check_call([
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(fast_mp3),
                    "-t", str(target),
                    "-c", "copy",
                    str(tmp_mp3)])
                tmp_mp3.rename(mp3)
                fast_mp3.unlink(missing_ok=True)
        print()


def assemble_wav():
    """Place each segment at its correct time offset in a full-length buffer."""
    total_samples = sec_to_samples(TOTAL_SEC)
    buf = bytearray(total_samples * 2)

    for name, start_frame, slot_sec, _ in SCENES:
        mp3 = TMP / f"{name}.mp3"
        wav = TMP / f"{name}.wav"
        mp3_to_wav(mp3, wav)
        pcm = read_wav_pcm(wav)

        start_sample = sec_to_samples(frames_to_sec(start_frame))
        byte_off     = start_sample * 2
        end_byte     = byte_off + len(pcm)
        if end_byte > len(buf):
            end_byte = len(buf)
            pcm = pcm[:end_byte - byte_off]
        buf[byte_off:end_byte] = pcm

    out_wav = OUT / "voiceover.wav"
    with wave.open(str(out_wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(buf))
    print(f"  Voiceover WAV → {out_wav}")
    return out_wav


def merge_and_caption(wav):
    silent = OUT / "skillberry-demo-silent.mp4"
    audio  = OUT / "skillberry-demo-audio.mp4"
    final  = OUT / "skillberry-demo-final.mp4"
    srt_esc = str(SRT).replace(":", "\\:")

    print("  Merging audio ...")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(silent), "-i", str(wav),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        str(audio)])

    print("  Burning captions ...")
    subprocess.check_call([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(audio),
        "-vf", (
            f"subtitles={srt_esc}"
            ":force_style='FontName=Arial,FontSize=14,Bold=0,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H80000000,Outline=2,Shadow=1,"
            "Alignment=2,MarginV=28'"
        ),
        "-c:a", "copy",
        str(final)])
    print(f"\n  ✅  {final}  ({final.stat().st_size/1e6:.0f} MB)")


if __name__ == "__main__":
    print("\n═══ Rebuilding voiceover ═══\n")
    print("Step 1  Generating / fitting TTS segments ...")
    generate_tts()
    print("\nStep 2  Assembling voiceover WAV ...")
    wav = assemble_wav()
    print("\nStep 3  Merging + captioning ...")
    merge_and_caption(wav)
    print()
