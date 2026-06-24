---
description: Scaffold a new WellForge project — interview, stack recommendation, generation, connections
argument-hint: <short product description> (optional — interview fills the gaps)
---

Scaffold a new WellForge project end-to-end: analyze what's being built, recommend a stack,
generate from the versioned template, verify it builds, and guide tool connections
(load the **connections** skill for that last stage).

Product: $ARGUMENTS

## Stage 1 — Understand the product

Interview with AskUserQuestion (batch, max 2 rounds). You need:
- Product type: internal tool / customer-facing app / API-only service / prototype.
- Scale & lifetime: throwaway experiment vs long-lived product; expected load.
- Domain complexity: rich domain logic and transactions vs thin CRUD/aggregation.
- Team & ecosystem constraints: who maintains it, existing systems it must talk to.
- Anything already decided (DB, hosting, auth provider) — record as constraints.

## Stage 2 — Recommend a stack

Available presets (the only two — do not invent others):

| Preset | Sweet spot |
|---|---|
| `spring-kotlin-react` | rich domain logic, transactions, long-lived products, JVM ecosystem integration, Spring Modulith boundaries |
| `hono-react` | lightweight APIs, fast iteration, prototypes→small products, all-TypeScript team, edge/container deploys |

Recommend ONE with a 3-5 line rationale tied to the interview answers (and say why not
the other). If the product genuinely fits neither (mobile, ML pipeline, desktop), say so
and stop — don't force a preset. User confirms or overrides; their choice wins.

## Stage 3 — Generate

1. Locate the wellforge repo (checkout path or git URL — ask once, remember for the
   session). The template source is the REPO ROOT: one `copier.yml` serves all presets.
2. Collect the answers (read the root `copier.yml` for the full list): preset,
   project_name, project_slug, description, base_package (JVM preset), db, ci.
3. Run, from the target parent directory:
   ```bash
   uvx copier copy --trust <wellforge repo/URL> <project_slug> \
     --data preset=<preset> --data project_name=... [--data ...]
   ```
   (requires `uv`; if missing: `brew install uv` or `mise use -g uv`.)
   Prefer the git URL over a local path once wellforge is hosted — it makes
   `/wellforge:upgrade` work for every team member, not just this machine.
4. Initialize: `git init -b main && git add -A && git commit -m "chore: scaffold from <template> v<version>"`.
   The scaffold commit must be pristine — no manual edits before it.

## Stage 4 — Verify the build

In the generated project: `mise trust && mise install`, then `mise run install`,
`mise run build`, `mise run test`. All three must pass — this is the acceptance bar for
the scaffold itself. A failure here is a TEMPLATE bug: report it precisely (file a note
to add to the wellforge repo), apply the minimal local fix, and continue.

## Stage 5 — Connect

Load the **connections** skill and walk its checklists in order (GitHub, CI secrets,
MCP servers, environments/DB). Every connection ends with that checklist's verification
command — run it and show the output. Skip checklists the user declines; record skipped
ones in the project README under "Pending setup".

## Stage 6 — Hand off

Summarize: project path, template+version (from `.forge/manifest.json`), build/test
results, connections established vs skipped. Tell the user the project is spec-driven:
the natural next step is `/wellforge:spec <first feature>` (or `/wellforge:orchestrate`).

## Hard rules

- Never scaffold by hand or "adapt" template output structurally — if the template is
  wrong, that's a template bug to report (the upgrade path depends on projects staying
  template-shaped).
- Never edit `.forge/manifest.json` or `.copier-answers.yml`.
- One project per invocation.
