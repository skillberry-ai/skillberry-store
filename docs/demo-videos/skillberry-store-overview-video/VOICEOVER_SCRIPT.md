# Skillberry Store — Demo Video Voiceover Script
## Total target duration: ~6:20 (380 seconds)
## Format: [SCENE TITLE] | [TIMECODE] | [DURATION] | Voiceover text

---

## SCENE 01 — INTRO
**Timecode:** 0:00 – 0:09 | **Duration:** 9s

> *Welcome to Skillberry Store — a smart skills repository built for agentic workflows.*

---

## SCENE 02 — WHAT IS SBS
**Timecode:** 0:09 – 0:24 | **Duration:** 15s

> *Skillberry Store is a central place to manage every tool your AI agents need. Upload once, execute anywhere, and manage everything from a single service. It handles tools, skills, and snippets — with semantic search, lifecycle management, virtual MCP servers, and a rich plugin ecosystem.*

---

## SCENE 03 — INSTALLATION
**Timecode:** 0:24 – 0:44 | **Duration:** 20s

> *Installation is straightforward. You can install just the core service with pip, or bundle in the AI plugins in one command. To run with Docker, a single make command starts everything. After a few seconds, the web UI is live on port eight-zero-zero-two, the REST API on eight-thousand, and the MCP control endpoint is ready for any AI client.*

---

## SCENE 04 — CLI INTRO
**Timecode:** 0:44 – 1:02 | **Duration:** 18s

> *Skillberry Store includes an auto-generated command-line interface called sbs. It's built on top of restish and mirrors every single REST endpoint. Install the SDK, run sbs connect to point it at your server, and every operation — skills, tools, snippets, virtual MCP and NFS servers, plus all admin commands — is available at your fingertips.*

---

## SCENE 05 — CLI IMPORT
**Timecode:** 1:02 – 1:18 | **Duration:** 16s

> *Let's import our first skill. Skillberry supports three import paths: a GitHub URL, a ZIP file, or a local folder path. Here we use curl against the import Anthropic endpoint, pointing it at the PPTX skill on disk. The response confirms the skill was created with sixty-six tools and forty-three snippets — in a single call.*

---

## SCENE 06 — UI HOME
**Timecode:** 1:18 – 1:28 | **Duration:** 10s

> *The web UI launches automatically alongside the backend. From the dashboard you can navigate to Skills, Tools, Snippets, virtual MCP and NFS servers, Plugins, Observability, and the Admin panel.*

---

## SCENE 07 — UI SKILLS
**Timecode:** 1:28 – 1:42 | **Duration:** 14s

> *Here's the Skills library with our two imported skills — the PPTX skill with sixty-six tools, and the Summarizer with twenty-nine. Notice the auto-applied tags: anthropic, imported, quality-score, performance-score, and security-score. Those were generated automatically by the Evaluator and Security plugins on import.*

---

## SCENE 08 — IMPORT DIALOG
**Timecode:** 1:42 – 2:00 | **Duration:** 18s

> *Let's walk through the import dialog in the UI. Click Import Anthropic Skill on the Skills page and you get three source options. GitHub URL for pointing directly at any Anthropic skills repository. ZIP File for uploading an archive — perfect for air-gapped environments. And Local Folder for providing an absolute path on the server — ideal for CI/CD pipelines. One click and the entire skill tree, tools, snippets, and all documentation is imported.*

---

## SCENE 09 — IMPORT RESULT
**Timecode:** 2:00 – 2:14 | **Duration:** 14s

> *Here's the PPTX skill detail page after import. Sixty-six tools are listed as clickable tags, along with forty-three snippets. The description, tags, version, and last-modified timestamp are all tracked. You can export back to the Anthropic format, edit metadata, or delete the skill — with a cascade option to clean up all associated tools and snippets.*

---

## SCENE 10 — SKILL DETAIL
**Timecode:** 2:14 – 2:28 | **Duration:** 14s

> *Here's the Summarizer skill. Twenty-nine tools, two snippets — one of which is the full README documentation. The evaluator has already scored it nine out of ten for quality, eight for performance, and eight for security. Those scores are immediately searchable and filterable across the whole library.*

---

## SCENE 11 — UI TOOLS
**Timecode:** 2:28 – 2:44 | **Duration:** 16s

> *The Tools page shows all ninety-five tools from both skills in one table. You can sort by any column, filter by tags, switch between text and semantic search, and select multiple tools for bulk export or deletion. Each row shows the tool name, description, state, all its tags, the module file name, and version.*

---

## SCENE 12 — TOOL DETAIL
**Timecode:** 2:44 – 2:57 | **Duration:** 13s

> *Clicking a tool opens its detail page. Here we have create-underscore-bullet-underscore-summary from the Summarizer skill. We can see its programming language, packaging format, the full dependency graph, and the JSON parameter schema. There's also a Source Code tab showing the raw Python module.*

---

## SCENE 13 — TOOL EXECUTE
**Timecode:** 2:57 – 3:13 | **Duration:** 16s

> *To execute a tool, hit the Execute button. A dialog accepts the parameters as JSON, and when you confirm, the tool runs inside a Docker sandbox — completely isolated from the host. You get the result back as structured JSON. From the CLI, it's one sbs execute-tool command with a body flag. Same Docker sandbox, same isolation, scriptable for automation.*

---

## SCENE 14 — UI SNIPPETS
**Timecode:** 3:13 – 3:23 | **Duration:** 10s

> *Snippets are code fragments and documentation files imported alongside the tools. They're stored with syntax highlighting and searchable by content or tags — perfect for reference material, configuration templates, or shared utility code that tools depend on.*

---

## SCENE 15 — VIRTUAL MCP SERVERS
**Timecode:** 3:23 – 3:34 | **Duration:** 11s

> *Virtual MCP Servers let you expose any subset of tools as a standalone MCP endpoint. Create one from any skill, and it gets its own dedicated port and SSE URL. Point Claude, Cursor, or any MCP-compatible client at that URL and it instantly sees only the tools from that skill — clean, scoped, and independent.*

---

## SCENE 16 — VIRTUAL NFS SERVERS
**Timecode:** 3:34 – 3:44 | **Duration:** 10s

> *Virtual NFS Servers go one step further — they expose an entire skill as a mountable, read-only filesystem over WebDAV or NFSv3. Claude Code, rclone, or any filesystem-aware tool can mount and browse skill files directly, without going through the REST API at all.*

---

## SCENE 17 — PLUGINS OVERVIEW
**Timecode:** 3:44 – 3:58 | **Duration:** 14s

> *The Plugins page shows all installed extensions. Each plugin card displays its name, status — enabled or disabled — a description, and any action buttons. You can enable or disable individual plugins independently. Let's walk through the five most important ones.*

---

## SCENE 18 — PLUGIN: CONTENT EVALUATOR
**Timecode:** 3:58 – 4:14 | **Duration:** 16s

> *The Content Evaluator uses an LLM to analyse your skills and tools, then automatically tags them with numeric scores for quality, performance, and security. Here you can see the Summarizer skill scored nine out of ten for quality, eight for performance, and eight for security. Each score comes with a detailed written evaluation you can read in the skill's metadata. The scoring runs automatically on import, and you can re-trigger it at any time from the Plugins panel.*

---

## SCENE 19 — PLUGIN: SECURITY EVALUATOR
**Timecode:** 4:14 – 4:30 | **Duration:** 16s

> *The Security Evaluator is a dedicated security-focused plugin. It reviews each skill for vulnerabilities — input validation gaps, path-traversal risks, injection vectors, missing authentication, and known CVE exposure. The PPTX skill scored four out of ten because it accepts arbitrary file paths with no validation or sandboxing. That's immediately visible as a security-score colon four tag, so you know before you deploy it in a production agent. A companion SAST scanner using Bandit is also available for static code analysis.*

---

## SCENE 20 — PLUGIN: SKILL DEDUPLICATOR
**Timecode:** 4:30 – 4:46 | **Duration:** 16s

> *The Skill Deduplicator keeps your library clean. It uses LLM-based semantic comparison — not just name matching — to find near-identical skills. When a duplicate pair is found, it creates a notification in the UI with a Keep Both or Delete Duplicate decision. The decision management API lets you automate this in CI pipelines. The detected duplicates are also tagged so you can filter and review them at any time.*

---

## SCENE 21 — PLUGIN: SNIPPET CREATOR
**Timecode:** 4:46 – 5:02 | **Duration:** 16s

> *The Snippet Creator plugin lets you generate code from a natural language description. Describe what you want — for example, "a Python function that converts a list of dictionaries to a Markdown table" — and the LLM generates production-ready code, automatically infers the language and tags, and saves the result directly to the store. No copy-paste required. The LLM backend is configurable: OpenAI, IBM WatsonX, or any LiteLLM-compatible provider.*

---

## SCENE 22 — PLUGIN: SKILL OPTIMIZER
**Timecode:** 5:02 – 5:18 | **Duration:** 16s

> *The Skill Optimizer is the most powerful plugin. It exports a skill to a temporary directory, launches a Claude Code session inside a RunSpace container, applies optimizations — improving descriptions, fixing edge cases, adding type hints, consolidating tools — and then imports the result as a new skill named with an optimized suffix. The optimization rationale, list of changes, and source skill UUID are all saved as metadata. Re-running is always safe and idempotent.*

---

## SCENE 23 — CLI EXECUTE TOOL
**Timecode:** 5:18 – 5:34 | **Duration:** 16s

> *Back to the CLI for a quick demonstration of tool execution. First, use sbs search-tools to find the right tool with a natural language query. Then run sbs execute-tool with the tool name and a JSON body. The result comes back as structured data you can pipe into jq, write to a file, or integrate into any shell script or CI pipeline.*

---

## SCENE 24 — OBSERVABILITY
**Timecode:** 5:34 – 5:48 | **Duration:** 14s

> *Skillberry Store has built-in observability. The Observability page in the UI shows a live time-series chart with tabs for Skills Metrics, Tools Metrics, Snippets Metrics, Virtual MCP Metrics, and System Metrics. On the backend, Prometheus metrics are available on port eight-zero-nine-zero and OpenTelemetry traces go to Jaeger. Drop a Grafana dashboard on top and you have full production monitoring.*

---

## SCENE 25 — ARCHITECTURE
**Timecode:** 5:48 – 6:04 | **Duration:** 16s

> *The architecture is layered and pluggable. At the top, the Web UI and REST API. Alongside those, the MCP frontend and Virtual NFS servers. In the middle, the core data model — skills, tools, and snippets. Below that, Docker-sandboxed tool execution, pluggable storage backends — filesystem or GitHub — and the AI plugin layer. Everything is observable, versioned, and extensible.*

---

## SCENE 26 — OUTRO
**Timecode:** 6:04 – 6:20 | **Duration:** 16s

> *That's Skillberry Store. One service for managing, executing, and organizing every skill your AI agents need. Install with pip, start with make docker-run, and you're live in under a minute. Check the links on screen for the Web UI, REST API, and MCP endpoint. The repository is at github dot com slash skillberry-ai slash skillberry-store. Give it a try.*

---

## CAPTION NOTES
- Keep each caption segment to 1–2 lines, max 80 characters per line
- Target 2–5 words per second speaking pace
- Pause naturally after commas and periods
- Emphasize: **Skillberry Store**, **Docker sandbox**, plugin names, and port numbers
