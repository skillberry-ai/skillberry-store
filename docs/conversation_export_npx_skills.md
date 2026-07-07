# Conversation Export: `npx skills`, skills.sh, WebDAV, and Well-Known HTTP Skills

**Export date:** 2026-07-07 14:40 GMT+03:00

---

## User

npx. This is a command-line utility used by https://skills.sh . Your task is to study it including code and documentation and answer the following:1. What is its main function.2. How is it used to install skills, what are the possible agents etc3. Is it possible to use it to install skills from a source other than skills.sh. If so, what are the requirements of such source - protocol, port, structure of data, etc.

---

## Assistant

Below is what I found from the current `skills` CLI docs and source references.

## 1. Main function

`npx skills` is the command-line package manager for the **open agent skills ecosystem**: it installs, lists, removes, updates, discovers, and temporarily uses “skills” for AI coding agents. A skill is a reusable capability/instruction package that helps an agent perform a specific workflow, similar to a plugin or reusable prompt bundle. citeturn1search5turn1search16

`skills.sh` is mainly the **directory / leaderboard / discovery site** for these packages; the CLI that powers it is open source at `vercel-labs/skills`, and install telemetry helps rank skills on the leaderboard. citeturn1search5turn1search19

Typical CLI commands include:

```bash
npx skills add <source>
npx skills use <source>
npx skills list
npx skills find [query]
npx skills remove [skills]
npx skills update [skills]
npx skills init [name]
```

The README and npm package describe `skills` as “The CLI for the open agent skills ecosystem,” with support for OpenCode, Claude Code, Codex, Cursor, and many more agents. citeturn1search16turn1search3

---

## 2. How it is used to install skills

### Basic install

The core command is:

```bash
npx skills add vercel-labs/agent-skills
```

This resolves the source, downloads or clones it, discovers skills, and installs them into the appropriate agent skill directory. citeturn1search1turn1search7

### Installing a specific skill from a multi-skill repo

```bash
npx skills add vercel-labs/agent-skills --skill web-design-guidelines
```

You can repeat `--skill`, quote names with spaces, or use `'*'` to install all skills. citeturn1search16turn1search3

### Installing for a specific agent

```bash
npx skills add vercel-labs/agent-skills -a claude-code
npx skills add vercel-labs/agent-skills -a claude-code -a opencode
```

`--agent '*'` means install to all supported/detected agents, and `--all` is the non-interactive “install all skills to all agents” path. citeturn1search16turn1search3

### Project vs global install

By default, installation is project-scoped; with `-g` / `--global`, it installs into the user-level agent skill directory. citeturn1search16turn1search3

```bash
# Project-local
npx skills add vercel-labs/agent-skills

# Global
npx skills add vercel-labs/agent-skills -g
```

### Symlink vs copy

Interactive installation lets the user choose between symlink and copy mode: symlink creates a canonical source of truth and links agent directories to it, while copy creates independent copies. citeturn1search16turn1search15

```bash
# Force copy instead of symlink
npx skills add vercel-labs/agent-skills --copy
```

### What happens internally

The install pipeline is roughly:

1. `parseSource()` normalizes the source argument.
2. Git repos are cloned to a temporary directory, or direct providers are fetched.
3. `discoverSkills()` searches for `SKILL.md` files.
4. If multiple skills exist, the CLI prompts the user to select skills.
5. `detectInstalledAgents()` detects local agents.
6. The user chooses project/global scope and symlink/copy mode.
7. `installSkillForAgent()` installs into agent directories.
8. The lock file is updated for future update/install operations. citeturn1search7turn1search15

### Supported / possible agents

The README says the current CLI supports OpenCode, Claude Code, Codex, Cursor, and “68 more.” citeturn1search16turn1search2

Examples explicitly mentioned in Vercel’s changelog include:

- `amp`
- `antigravity`
- `claude-code`
- `clawdbot`
- `codex`
- `cursor`
- `droid`
- `gemini`
- `gemini-cli`
- `github-copilot`
- `goose`
- `kilo`
- `kiro-cli`
- `opencode`
- `roo`
- `trae`
- `windsurf` citeturn1search19

The source also contains support paths for agent directories such as `.agents/skills`, `.claude/skills`, `.cline/skills`, `.codex/skills`, `.continue/skills`, `.github/skills`, `.goose/skills`, `.opencode/skills`, `.openhands/skills`, `.qoder/skills`, `.windsurf/skills`, and others. citeturn1search12turn1search14

---

## 3. Can it install skills from sources other than `skills.sh`?

**Yes.** `skills.sh` is not the only source and is not required for installation. The CLI can install from GitHub, GitLab, generic Git URLs, direct skill URLs, well-known HTTP endpoints, and local paths. citeturn1search16turn1search8

### Supported source formats

The README lists these common formats:

```bash
# GitHub shorthand
npx skills add vercel-labs/agent-skills

# Full GitHub URL
npx skills add https://github.com/vercel-labs/agent-skills

# Direct path to a skill in a repo
npx skills add https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines

# GitLab URL
npx skills add https://gitlab.com/org/repo

# Any git URL
npx skills add git@github.com:vercel-labs/agent-skills.git

# Local path
npx skills add ./my-local-skills
```

These are documented in the README and npm package page. citeturn1search16turn1search3

DeepWiki’s source analysis also notes well-known endpoints and direct URLs, including examples like `https://example.com` with `/.well-known/skills/` and direct `https://docs.bun.com/skill.md`-style URLs. citeturn1search7turn1search8

---

## Requirements for a custom / non-`skills.sh` source

### A. Git repository source

A custom source can be any Git repository reachable by the local `git` client, including GitHub, GitLab, SSH URLs, HTTPS Git URLs, and other Git-compatible remotes. citeturn1search16turn1search8

Examples:

```bash
npx skills add https://gitlab.example.com/team/agent-skills.git
npx skills add git@internal-git.example.com:team/agent-skills.git
npx skills add ssh://git@internal-git.example.com:2222/team/agent-skills.git
```

**Protocol / port requirements:** for Git sources, the protocol and port are whatever your Git client supports and can authenticate to: commonly HTTPS on 443, SSH on 22, or an explicit custom SSH/HTTPS port in the URL. The CLI’s job is to parse the source and hand repository fetching to Git; there is no evidence that the CLI requires the source to be hosted on `skills.sh`. citeturn1search8turn1search7

### B. Local path source

A source can be a local directory, such as:

```bash
npx skills add ./my-local-skills
npx skills add ../shared-skills
```

The parser treats relative paths, absolute paths, and Windows drive-style paths as local sources. citeturn1search8turn1search13

### C. Direct HTTP(S) `SKILL.md` source

The source handling docs describe direct skill URLs as HTTPS URLs ending in `/skill.md`, fetched through the provider system rather than cloned as a repo. citeturn1search8turn1search23

Example:

```bash
npx skills add https://example.com/my-skill/skill.md
```

**Protocol / port requirements:** documented examples use `https://`; the normal port is 443 unless the URL includes a custom port, assuming the runtime `fetch` can access it. citeturn1search8turn1search23

### D. Well-known endpoint source

The source docs mention well-known endpoints such as:

```bash
npx skills add https://example.com
```

where the site exposes skills under `/.well-known/skills/`. citeturn1search7turn1search8

The exact endpoint schema is not fully visible in the public snippets I could access, but the documented pattern is that the host is resolved through a well-known skills endpoint and returns skill data that the CLI can convert into installable skills. citeturn1search7turn1search8

---

## Required data structure of a skill

A skill is a directory containing at minimum:

```text
my-skill/
└── SKILL.md
```

`SKILL.md` must start with YAML frontmatter containing at least `name` and `description`. citeturn1search22turn1search12

Minimal example:

```markdown
---
name: my-skill
description: Do X for Y projects. Use when the user asks about X or mentions Y.
---

# Instructions

Step-by-step instructions for the agent go here.
```

The docs state that `name` and `description` are required; `name` should match the parent directory name, use lowercase letters/numbers/hyphens, and the description should explain what the skill does and when to use it. citeturn1search22turn1search12

A skill package can be a repo or directory containing one or more skill folders, each with its own `SKILL.md`; optional supporting files such as scripts, references, or assets can live alongside the `SKILL.md` and be loaded when the skill instructs the agent to use them. citeturn1search22turn1search7

---

## Bottom line

Yes, you can host skills outside `skills.sh`. For a private/internal source, the easiest supported patterns are:

```bash
# Internal Git repo
npx skills add git@internal-git.example.com:ai/skills.git

# Internal Git repo on custom SSH port
npx skills add ssh://git@internal-git.example.com:2222/ai/skills.git

# Local folder
npx skills add ./company-skills

# Direct HTTPS skill file
npx skills add https://skills.internal.example.com/security-review/skill.md
```

The source just needs to expose valid skill content: a folder or fetched file with `SKILL.md`, YAML frontmatter containing `name` and `description`, and Markdown instructions for the agent. citeturn1search22turn1search8

---

## User

I have a WebDAV source that contains an entire skill - SKILL.md, scripts, prompts etc. Can I use it directly with npx?

---

## Assistant

Short answer: **not directly as a WebDAV directory URL**.

`npx skills add` supports GitHub/GitLab repos, generic Git URLs, local paths, and direct HTTPS URLs that point to a `skill.md`/`SKILL.md`-style file via its provider system; the documented source handling does **not** list WebDAV as a supported remote directory protocol. citeturn2search31turn2search34

So this probably **will not work** as an installable full skill folder:

```bash
npx skills add https://webdav.example.com/skills/my-skill/
```

because the CLI expects either a cloneable repo, a recognized provider/direct skill file, or a local filesystem directory. citeturn2search34turn2search33

## What you can do instead

### Option 1 — Mount or sync WebDAV locally, then install from local path

This is the best fit if your WebDAV folder contains the whole skill:

```text
my-skill/
├── SKILL.md
├── scripts/
├── prompts/
└── ...
```

Mount/sync it locally, then run:

```bash
npx skills add ./my-skill
```

or, if it is a package containing multiple skills:

```bash
npx skills add ./company-skills
```

Local paths are a supported source type, and a skill is expected to be a directory containing at least `SKILL.md`; supporting files can live alongside it. citeturn2search34turn2search36

For example, with `rclone`:

```bash
rclone copy webdav:skills/my-skill ./my-skill
npx skills add ./my-skill
```

or with a mounted WebDAV directory:

```bash
npx skills add /mnt/webdav/skills/my-skill
```

### Option 2 — Put the WebDAV content behind Git

If you can mirror the WebDAV folder into Git, then the CLI can install it directly:

```bash
npx skills add git@internal-git.example.com:ai/skills.git
```

or:

```bash
npx skills add https://git.example.com/ai/skills.git
```

Generic Git URLs are supported, not only `skills.sh` or GitHub. citeturn2search31turn2search34

### Option 3 — Use a direct `SKILL.md` URL only if the skill is self-contained

If your WebDAV server exposes the file over HTTPS, this *may* work for a single-file skill:

```bash
npx skills add https://webdav.example.com/skills/my-skill/SKILL.md
```

But this is only suitable if the skill does **not** depend on sibling files such as `scripts/`, `prompts/`, references, or assets, because the direct-URL provider path is documented as fetching skill content from a direct URL rather than cloning/downloading an entire directory tree. citeturn2search33turn2search34

Given your case includes `SKILL.md`, scripts, prompts, etc., I would **not** rely on a direct `SKILL.md` URL.

## Required structure after mounting/syncing

Make sure the local directory looks like:

```text
my-skill/
├── SKILL.md
├── scripts/
│   └── ...
├── prompts/
│   └── ...
└── references/
    └── ...
```

And `SKILL.md` must include YAML frontmatter with at least:

```markdown
---
name: my-skill
description: Use this skill when ...
---

# Instructions

...
```

The `name` and `description` fields are required, and the docs recommend that the name match the parent directory and use lowercase letters, numbers, and hyphens. citeturn2search36

## Bottom line

For a WebDAV-hosted **full skill directory**, use this pattern:

```bash
# 1. Sync or mount WebDAV locally
rclone copy webdav:skills/my-skill ./my-skill

# 2. Install with npx skills
npx skills add ./my-skill -a claude-code
```

Direct WebDAV directory installation is not currently a documented/supported `npx skills add` source. The practical choices are **local mount/sync** or **mirror to Git**.

---

## User

Is the "bare HTTP" method capable of handling skills that contain more than SKILL.md?

---

## Assistant

Yes — **but only via the “well-known HTTP provider” path, not by pointing at an arbitrary HTTP/WebDAV directory listing.**

There are two different HTTP-ish cases:

## 1. Direct `SKILL.md` URL — mostly **single-file only**

If you give the CLI a direct URL to a skill file, the provider interface fetches and parses a `SKILL.md`-style document into a `RemoteSkill` object containing fields like `name`, `description`, `content`, `installName`, and `sourceUrl`; that model is centered on the Markdown content itself, not an arbitrary directory tree. citeturn3search38

So this is **not enough** for a full skill with scripts/prompts:

```bash
npx skills add https://example.com/my-skill/SKILL.md
```

It may install the instructions, but it is not the documented path for fetching sibling files such as:

```text
scripts/run.sh
prompts/review.md
references/rules.md
```

## 2. Well-known HTTP endpoint — **yes, can include multiple files**

The current source includes a `WellKnownProvider` that is explicitly designed for organizations to publish skills over HTTP(S) using RFC 8615-style well-known URIs. It supports publishing at:

```text
https://example.com/.well-known/agent-skills/
```

with a legacy fallback:

```text
https://example.com/.well-known/skills/
```

The provider first checks `/.well-known/agent-skills/index.json`, then falls back to `/.well-known/skills/index.json`. citeturn3search39turn3search40

Importantly, its `index.json` skill entry includes a `files: string[]` field described as “Array of all files in the skill directory,” and the provider has a `WellKnownSkill` type with “all files in the skill, keyed by relative path.” citeturn3search39

So **well-known HTTP can represent a full skill**, not just `SKILL.md`.

A likely structure would be:

```text
https://example.com/.well-known/agent-skills/index.json
https://example.com/.well-known/agent-skills/my-skill/SKILL.md
https://example.com/.well-known/agent-skills/my-skill/scripts/run.sh
https://example.com/.well-known/agent-skills/my-skill/prompts/review.md
```

With `index.json` shaped like:

```json
{
  "skills": [
    {
      "name": "my-skill",
      "description": "Does X using local scripts and prompts.",
      "files": [
        "SKILL.md",
        "scripts/run.sh",
        "prompts/review.md"
      ]
    }
  ]
}
```

Then installation should be from the host or well-known path, for example:

```bash
npx skills add https://example.com
```

or:

```bash
npx skills add https://example.com/.well-known/agent-skills/my-skill
```

The provider supports URLs such as the domain root, a path root, the well-known endpoint, and a specific skill path under `/.well-known/agent-skills/<skill-name>`. citeturn3search39

## For your WebDAV case

If your WebDAV server only exposes a normal directory listing, then **probably no**:

```bash
npx skills add https://webdav.example.com/skills/my-skill/
```

The CLI is not documented as crawling arbitrary WebDAV/HTTP directory listings.

But if you can expose your WebDAV content through the **well-known structure** with an `index.json` and stable HTTP(S) file URLs, then **yes**, it can handle a full multi-file skill. The provider accepts HTTP(S) URLs and matches non-Git HTTP(S) endpoints as a fallback well-known provider. citeturn3search39turn3search40

## Practical recommendation

For a WebDAV-backed full skill, best options are:

```bash
# Option A: expose a well-known endpoint
npx skills add https://skills.example.com
```

or:

```bash
# Option B: sync/mount WebDAV locally
npx skills add /mnt/webdav/my-skill
```

or:

```bash
# Option C: mirror to Git
npx skills add git@internal-git.example.com:team/skills.git
```

If you want direct network installation without Git, the **well-known HTTP provider** is the path that can include `SKILL.md` plus scripts/prompts/etc.

---

## User

Does the well-known structure co-locate well with the Anthropic skill structure?

---

## Assistant

Yes — **it co-locates pretty well, with one extra publishing wrapper**.

The **Anthropic / Agent Skills structure** is already the same core structure the `skills` CLI expects: a skill is a folder with `SKILL.md` plus optional directories such as `scripts/`, `references/`, `assets/`, and any other files. citeturn4search38turn4search50

The **well-known HTTP provider** adds an HTTP discovery layer around that same folder structure: it expects `/.well-known/agent-skills/index.json`, and each skill entry has `name`, `description`, and a `files` array listing all files in that skill directory. citeturn3search39turn4search40

## Recommended layout

If your Anthropic-compatible skill is:

```text
my-skill/
├── SKILL.md
├── scripts/
│   └── validate.py
├── prompts/
│   └── review.md
├── references/
│   └── guide.md
└── assets/
    └── template.md
```

You can publish it as:

```text
https://skills.example.com/.well-known/agent-skills/index.json
https://skills.example.com/.well-known/agent-skills/my-skill/SKILL.md
https://skills.example.com/.well-known/agent-skills/my-skill/scripts/validate.py
https://skills.example.com/.well-known/agent-skills/my-skill/prompts/review.md
https://skills.example.com/.well-known/agent-skills/my-skill/references/guide.md
https://skills.example.com/.well-known/agent-skills/my-skill/assets/template.md
```

Then `index.json` would look like:

```json
{
  "skills": [
    {
      "name": "my-skill",
      "description": "Does X using bundled scripts, prompts, references, and assets.",
      "files": [
        "SKILL.md",
        "scripts/validate.py",
        "prompts/review.md",
        "references/guide.md",
        "assets/template.md"
      ]
    }
  ]
}
```

Then install with:

```bash
npx skills add https://skills.example.com
```

or, for a specific skill path:

```bash
npx skills add https://skills.example.com/.well-known/agent-skills/my-skill
```

The provider explicitly supports root-domain discovery, well-known endpoint discovery, and specific skill paths under `/.well-known/agent-skills/<skill-name>`. citeturn3search39

## Important caveat

It does **not** mean you can expose an arbitrary existing Anthropic repo layout like this and expect automatic crawling:

```text
https://skills.example.com/skills/my-skill/SKILL.md
https://skills.example.com/skills/my-skill/scripts/...
```

unless you also expose the well-known index and map the files where the provider expects them. The well-known provider discovers skills through `/.well-known/agent-skills/index.json` or legacy `/.well-known/skills/index.json`, not by crawling arbitrary directories. citeturn3search39turn4search40

## Best co-location pattern

If your canonical source is already Anthropic-style:

```text
skills/
└── my-skill/
    ├── SKILL.md
    ├── scripts/
    ├── references/
    └── assets/
```

then keep that as-is, and publish a generated/mirrored view:

```text
.well-known/
└── agent-skills/
    ├── index.json
    └── my-skill/
        ├── SKILL.md
        ├── scripts/
        ├── references/
        └── assets/
```

This preserves full Anthropic compatibility, while adding only the discovery manifest needed for `npx skills add https://...`.

## Bottom line

**Yes, well-known HTTP co-locates cleanly with Anthropic skills.** The actual skill folders can remain valid Anthropic/Agent Skills folders. You just need to add:

1. `/.well-known/agent-skills/index.json`
2. A public HTTP(S) path for each listed file
3. The `files` array listing `SKILL.md` and all supporting files

That makes it suitable for multi-file skills, including `scripts/`, `prompts/`, `references/`, and `assets/`.

---

## User

Please export this entire conversation, including all questions and anseers, to a markdown file.
