# WellForge — Implementation Plan

Status legend: ☐ todo · ◐ in progress · ☑ done

---

## Phase 0 — Foundations & decisions (½ day)

Goal: lock the decisions everything else depends on.

- ☑ Vehicle: **hybrid** — Claude Code plugin + Copier templates + shared CI gates.
  A plugin alone cannot version generated projects or enforce gates in CI.
- ☑ Spec framework: **thin in-house layer** (spec → plan → tasks), spec-kit-style,
  packaged as plugin commands. Rationale vs. alternatives tried:
  - *BMAD*: powerful but heavyweight; too much ceremony for typical welld project size.
  - *superpowers*: great skill-authoring patterns — borrow the style, not the framework.
  - *Kiro*: good spec UX but tied to its own IDE/runtime.
  - *cc-sdd / spec-kit*: closest to what we want — adopt the spec→plan→tasks shape,
    but own the prompts so they encode welld conventions and don't churn under us.
- ☑ Templating engine: **Copier** — only mainstream engine with first-class
  `copier update` (re-apply evolved template to an existing project) + migration tasks.
  Requires `uv`/`pipx` on dev machines (acceptable; we already require mise).
- ☑ Restructure repo to target layout (`docs/`, `templates/`, `gates/` alongside
  `welld-dev-plugin/`); git-init history checkpoint.

## Phase 1 — Spec-driven framework (Pillar 1) (1–2 days)

Goal: one standardized path from idea to reviewed task list, stored in the repo.

- ☐ `commands/spec.md` — `/spec <feature>`: interview → write `specs/NNN-slug/spec.md`
  (problem, user stories w/ acceptance criteria, non-goals, open questions).
- ☐ `commands/plan.md` — `/plan`: read active spec → `plan.md` (architecture, data model,
  API contracts, test strategy). Requires spec sign-off marker before proceeding.
- ☐ `commands/tasks.md` — `/tasks`: derive ordered, dependency-aware task list
  (`tasks.md`) with per-task acceptance checks; tasks reference spec sections.
- ☐ `skills/spec-driven/SKILL.md` — conventions: directory layout (`specs/NNN-slug/`),
  status frontmatter (draft → approved → in-progress → done), drift rule
  (code change that contradicts spec ⇒ update spec first).
- ☐ Wire existing `stop-verify.sh` hook to check spec drift against this format.

Acceptance: a feature can go idea → spec → plan → tasks entirely via commands, output
files are diff-reviewable, and a second developer can pick up the tasks cold.

## Phase 2 — Multi-agent team (Pillar 2) (1–2 days)

Goal: 7 role agents with crisp boundaries, each producing a defined artifact.

| Agent file | Role | Primary artifact | Tools |
|---|---|---|---|
| `agents/product-owner.md` | scope, user stories, acceptance criteria | spec.md sections | read-only |
| `agents/architect.md` | system design, ADRs, stack fit | plan.md, ADRs (reuse adr-writer) | read-only |
| `agents/designer.md` | UX flows, component inventory, a11y | design notes in spec | read-only + playwright |
| `agents/frontend-dev.md` | implement FE tasks | code | full |
| `agents/backend-dev.md` | implement BE tasks | code | full |
| `agents/devops.md` | CI/CD, IaC, MCP/CLI connections | pipeline + infra files | full |
| `agents/quality-engineer.md` | test plans, gate verdicts, exploratory testing | test code + gate report | full + playwright |

- ☐ Write the 7 agent definitions (system prompt: role, inputs it expects, artifact it
  must return, what it must NOT do — e.g. PO never writes code).
- ☐ Keep `owasp-reviewer` and `adr-writer` as specialists callable by QE/Architect.
- ☐ Each agent's prompt references the spec format from Phase 1 (agents read
  `specs/NNN-slug/` as their contract).

Acceptance: each agent invoked standalone on a sample spec produces its artifact without
overstepping its role.

## Phase 3 — Orchestrator (Pillar 3) (1–2 days)

Goal: one entry point that routes work through the team instead of ad-hoc prompting.

- ☐ `commands/orchestrate.md` — `/forge:orchestrate <goal>`: classifies the request
  (new feature / bugfix / refactor / infra), then drives the pipeline:
  - new feature → PO (spec) → Architect (plan) → [Designer ∥ if UI] → tasks → FE/BE devs
    in parallel per task → QE verdict → done.
  - bugfix → QE (repro test) → dev (fix) → QE (verify).
- ☐ Handoff contract: each stage's artifact is written to disk before the next stage
  starts (orchestrator passes file paths, not chat context — survives compaction).
- ☐ Human gates: orchestrator pauses for user approval after spec and after plan
  (AskUserQuestion), never auto-approves its own work.
- ☐ Parallelism rule: FE/BE tasks with no dependency edge run as parallel subagents.

Acceptance: `/forge:orchestrate "add CSV export to reports"` runs the full chain on a
sample project with exactly 2 human approval pauses.

## Phase 4 — Scaffolder + connection layer (Pillar 4) (3–5 days, biggest chunk)

Goal: product description in → running repo with connections out, in <30 min.

- ☐ `templates/spring-kotlin-react/` — Copier template extracted from
  `skills/springboot-scaffold/scripts/scaffold.sh` + the react-ts-vite setup reference.
  Answers file drives: project name, modules, DB, auth mode, CI provider.
- ☐ `templates/hono-react/` — second preset (validates the template abstraction;
  two presets prevent overfitting to one stack).
- ☐ Every template emits `.forge/manifest.json` `{ template, version, answers }` and
  `_copier_answers.yml` — the upgrade contract for Phase 6.
- ☐ Every template emits a project-local `CLAUDE.md` + `.claude/settings.json`
  pre-wired for the plugin (the scaffold is AI-ready on first open).
- ☐ `commands/new.md` — `/forge:new`: interview (product type, team, constraints) →
  stack recommendation with rationale → run `copier copy` → verify build passes.
- ☐ Connection layer — `skills/connections/SKILL.md` + per-tool references:
  standardized MCP/CLI setup checklists (GitHub repo + branch protection, CI secrets,
  registry, Sentry/observability, DB). Each checklist ends with a **verification
  command** so "connected" is objective, not assumed.

Acceptance: `/forge:new` on a clean machine produces a building, CI-green, AI-ready
repo for both presets; all connections verified by their check commands.

## Phase 5 — Quality gates (Pillar 5) (2–3 days)

Goal: the same measurable bar everywhere; CI is the enforcement point, hooks are the
fast local feedback.

- ☐ `gates/workflows/` — reusable GitHub Actions (`workflow_call`):
  - `quality-node.yml`: ESLint (error-level), `tsc --noEmit`, Vitest coverage ≥ **80%**
    lines / **70%** branches, `osv-scanner` (fail on high+), `semgrep` SAST.
  - `quality-jvm.yml`: ktlint, detekt, JaCoCo coverage ≥ **80%**, OWASP dep-check /
    osv-scanner, semgrep.
- ☐ `gates/configs/` — shared `eslint-config-welld`, detekt/ktlint rulesets, semgrep
  ruleset; templates *reference* these (npm package / maven artifact / remote config),
  never copy them — so a threshold bump propagates without re-scaffolding.
- ☐ Templates call the reusable workflows pinned to a `gates` semver tag.
- ☐ Plugin side: extend `post-lint.sh` + `stop-verify.sh` to run the same checks
  locally (same configs ⇒ no local/CI drift); QE agent reads gate output and reports
  pass/fail with numbers, not vibes.
- ☐ Threshold changes require a PR to `gates/` (review = the only discretion point).

Acceptance: a scaffolded project with a deliberately under-tested module fails CI with
an actionable message; fixing coverage turns it green; no per-project config edits.

## Phase 6 — Lifecycle & upgrades (Pillar 6) (2–3 days)

Goal: presets evolve, fleets follow.

- ☐ Semver discipline for templates: patch = cosmetic, minor = additive, major =
  needs migration. Tag releases in this repo.
- ☐ `commands/upgrade.md` — `/forge:upgrade`: reads `.forge/manifest.json`, runs
  `copier update` to target version, resolves conflicts with AI assistance (this is
  where the plugin shines — merge conflicts in templated files get explained and
  resolved interactively), runs the quality gates, updates manifest.
- ☐ Per-version migration tasks in templates (Copier `_migrations`) for mechanical
  steps; AI handles the judgment calls.
- ☐ `gates/` upgrades are decoupled: pinned tag bump in CI file, usually a one-line PR.
- ☐ Fleet visibility: simple registry (`docs/fleet.md` or a script hitting GitHub API)
  listing generated projects + their template versions → know what's outdated.

Acceptance: scaffold with template v1.0.0 → evolve template to v1.1.0 (add a file,
change a config) → `/forge:upgrade` brings the old project to v1.1.0 with green gates
and preserved local changes.

## Phase 7 — Pilot & rollout (1 week calendar, low effort)

- ☐ Use WellForge end-to-end on the next real project start; time-box and measure
  (setup time, gate violations caught, friction notes).
- ☐ Fix the top friction points; cut `v1.0.0` of plugin + templates + gates.
- ☐ Onboarding doc for the team (install marketplace, one happy-path walkthrough).
- ☐ Ownership: PRs to `templates/` and `gates/` require review; changelog per release.

---

## Order & dependencies

```
P0 ─► P1 (spec) ─► P2 (agents) ─► P3 (orchestrator) ─► P7
        └────────► P4 (scaffolder) ─► P5 (gates) ─► P6 (lifecycle) ─► P7
```

P1+P4 can start in parallel after P0. Total: ~3 weeks of focused effort.

## Risks

- **Copier requires Python tooling** on dev machines → mitigate: install via `mise`/`uv`,
  document in onboarding; fallback is `npx giget` + custom diff (worse, avoid).
- **Template sprawl** → hard rule: max 2 presets until Phase 7 proves the model.
- **Agent role bleed** (PO writing code) → explicit "must not" lists in agent prompts,
  checked during pilot.
- **Gates too strict at first** → start thresholds at current-reality levels, ratchet up
  via `gates/` PRs; a gate everyone overrides is worse than no gate.
- **Claude Code plugin API churn** → plugin format is markdown-based and stable; keep
  hooks POSIX-sh portable.
