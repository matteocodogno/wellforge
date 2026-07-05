# WellForge — public presentation site

A single, self-contained landing page (`index.html`, no build step) presenting WellForge:
the problem, the 6 pillars, the three-layer architecture, rigor tiers, and how to get started.

## Preview locally

```bash
open site/index.html          # macOS — just open the file
# or serve it:
python3 -m http.server -d site 8000   # then visit http://localhost:8000
```

## Publish (deliberate, manual — not automatic)

Publishing is **outward-facing and hard to reverse**, and WellForge is marked internal
tooling, so it does not deploy on push. Going live is a two-step human action:

1. **Decide it should be public.** If the repo is private, making the site reachable means
   making the repo public (or using GitHub Enterprise private Pages). That's a Welld call.
2. **Enable + deploy.** Settings → Pages → Source: **GitHub Actions**. Then run the
   **"Deploy site"** workflow from the Actions tab (`workflow_dispatch`). It publishes `site/`.

To take it down later: disable Pages in Settings, or remove `.github/workflows/pages.yml`.

## Editing

Content is plain HTML with embedded CSS — edit `index.html` directly. Keep the version badges
in the hero in sync with the plugin/template/gates release series.
