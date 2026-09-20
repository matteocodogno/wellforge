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
- Product type: internal tool / customer-facing app / API-only service / prototype — or
  **infrastructure** (the cloud resources an app runs on, rather than the app). Ask this
  explicitly: an IaC project is a first-class preset here, and a user who says "set up our
  GCP environment" will otherwise be pushed toward an application stack they didn't ask for.
- Scale & lifetime: throwaway experiment vs long-lived product; expected load.
- Domain complexity: rich domain logic and transactions vs thin CRUD/aggregation.
- Team & ecosystem constraints: who maintains it, existing systems it must talk to.
- Anything already decided (DB, hosting, auth provider) — record as constraints.

From the "scale & lifetime" answer, also settle the **rigor tier** (load the **rigor-tiers**
skill; it becomes the project default in `.forge/manifest.json`):
- throwaway experiment / feasibility PoC → `spike`
- first release to validate with users → `mvp`
- long-lived product / critical use case → `production` (default)

State the tier you'll use and why; the user can override. It sets how strict generated CI is
(`spike` = build + secret-scan floor; `mvp` = coverage advisory; `production` = full gates) and
can be raised later with `/wellforge:promote`.

## Stage 2 — Recommend a stack

**The preset list is the root `copier.yml`'s `preset:` choices — read it, don't trust this
table's age.** Never invent a preset that isn't in that list; if the two disagree,
`copier.yml` wins and this table is the bug. As of writing, three:

| Preset | Sweet spot |
|---|---|
| `spring-kotlin-react` | rich domain logic, transactions, long-lived products, JVM ecosystem integration, Spring Modulith boundaries |
| `hono-react` | lightweight APIs, fast iteration, prototypes→small products, all-TypeScript team, edge/container deploys |
| `pulumi-gcp-ts` | **infrastructure, not an application** — Pulumi IaC in TypeScript on GCP: stacks, ComponentResources, CrossGuard policy, mock tests |

The first two are alternatives to each other; `pulumi-gcp-ts` is **orthogonal** to both — it
answers "what runs this", not "what is this". So:

- Application project → recommend ONE of the two app presets with a 3-5 line rationale tied
  to the interview answers, and say why not the other.
- Infrastructure project → `pulumi-gcp-ts`. Do not "fall back" to an app preset.
- Both needed (an app *and* its infra) → they are two projects, and this command does one per
  invocation (hard rules). Scaffold the one they need first, and tell them the exact second
  command to run for the other.
- Genuinely fits none (mobile, ML pipeline, desktop) → say so and stop; don't force a preset.
  "Fits none" now means none of **three**, and an infra project is no longer one of them.

User confirms or overrides; their choice wins.

## Stage 3 — Generate

1. Locate the wellforge repo (checkout path or git URL — ask once, remember for the
   session). The template source is the REPO ROOT: one `copier.yml` serves all presets.
2. Collect the answers (read the root `copier.yml` for the full list — questions are
   preset-conditional, so let the file tell you which apply): always `preset`,
   `project_name`, `project_slug`, `description`, `ci`, `rigor`; plus `base_package` for
   `spring-kotlin-react`, `db` for the two app presets, and `gcp_project` + `gcp_region` for
   `pulumi-gcp-ts` (which has no `db`).
3. Run, from the target parent directory:
   ```bash
   uvx copier copy --trust <wellforge repo/URL> <project_slug> \
     --data preset=<preset> --data project_name=... [--data ...]
   ```
   (requires `uv`; if missing: `brew install uv` or `mise use -g uv`.)
   Prefer the git URL over a local path once wellforge is hosted — it makes
   `/wellforge:upgrade` work for every team member, not just this machine.
4. **Stamp the plugin version into `.forge/manifest.json`** — copier cannot, and this is
   the only record of which plugin set the project up (its `AGENTS.md` conventions, spec
   formats, trace schema and hooks all move with the plugin):

   ```jsonc
   // added to the generated manifest, alongside template/version/answers
   "plugin": { "version": "<this plugin's version>", "set_by": "new", "at": "<today>",
               "marketplace": "<where the plugin came from>" }
   ```

   Read the version from the installed plugin's own `.claude-plugin/plugin.json` — never
   from memory, and never a copier answer (a persisted answer would replay the scaffold-time
   version forever; see the template-contract skill for why).

   Record **where the plugin came from** too, in the same object:

   ```bash
   # marketplace install → "wellforge@wellforge"; nothing here → "local" (--plugin-dir)
   jq -r '.plugins | keys[] | select(startswith("wellforge@"))' \
     ~/.claude/plugins/installed_plugins.json 2>/dev/null | head -1
   ```

   A project set up by a checkout and a project set up by a published release are different
   provenance, and only one of them can be reproduced by a teammate. `/wellforge:doctor`
   reports it; if it is `local`, doctor says so rather than implying the release is pinned.

5. Initialize: `git init -b main && git add -A && git commit -m "chore: scaffold from <template> v<version>"`.
   The scaffold commit must be pristine — no manual edits before it, and the manifest
   including its `plugin` object is part of that first commit.

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
- The root `copier.yml`'s `preset:` choices are the authoritative preset list. Read it before
  recommending; a preset that exists there but not in Stage 2's table is reachable and this
  file is out of date — say so rather than steering the user away from it.
- One project per invocation.
