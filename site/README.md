# Skillberry Store — marketing / docs site

Plain HTML + CSS. **No framework, no build step, no JS build.** The `site/`
directory is published verbatim to GitHub Pages by
`.github/workflows/pages.yml`.

Live URL: https://skillberry-ai.github.io/skillberry-store/

## Files

| Path | Purpose |
|------|---------|
| `index.html` | Home / landing page |
| `getting-started.html` | Install, run, open the UI, import skills |
| `features.html` | Tools, skills, snippets, search, VMCP, vNFS, observability |
| `plugins.html` | The plugin ecosystem |
| `architecture.html` | Stack, MCP frontend/backend, source layout |
| `cli.html` | The `sbs` CLI |
| `style.css` | Single stylesheet (CSS variables, brand tokens) |
| `assets/` | Logo, UI screenshots, highlights video |
| `robots.txt`, `sitemap.xml` | SEO helpers |

Content is sourced only from this repository (README, `docs/`, the demo-video
voiceover script, and code) — nothing is borrowed from other projects.

## Authoring conventions

- **Relative links** between pages and assets (the site is served at the project
  sub-path `/skillberry-store/`). Absolute URLs appear only in
  `canonical` / OpenGraph / `sitemap.xml`.
- **Announcement strip + nav + footer are duplicated** in every HTML file (no
  includes/partials). When you change any of the three, edit every page. Consider
  a small build script if the site grows past ~10 pages. The `.announce` strip at
  the top of each `<body>` carries the current launch news (the introduction
  blog); retire it by deleting that block from all six pages — the same links
  live permanently in the footer's **Resources** column.
- **Cache-busting:** the stylesheet is linked as `style.css?v=YYYYMMDD-N`. Bump
  this query string whenever you edit `style.css`, or browsers serve the stale
  copy. (Current: `?v=20260909-1`.)
- **Fonts** load from Google Fonts (Red Hat Display + JetBrains Mono).
- Set the `active` class on the current page's nav link.

## Local preview

```bash
scripts/preview-site.sh            # serves site/ at http://localhost:8080
PORT=9000 scripts/preview-site.sh  # custom port
```

## Deploy

Pushing changes under `site/**` to `main` triggers the `Deploy GitHub Pages`
workflow (also runnable via **workflow_dispatch**). One-time setup: in the repo
**Settings → Pages → Source**, select **"GitHub Actions"**.
