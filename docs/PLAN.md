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
  `wellforge-plugin/`); git-init history checkpoint.

## Phase 1 — Spec-driven framework (Pillar 1) (1–2 days)

Goal: one standardized path from idea to reviewed task list, stored in the repo.

- ☑ `commands/spec.md` — `/wellforge:spec <feature>`: interview → write
  `specs/NNN-slug/spec.md` (problem, user stories w/ acceptance criteria, non-goals,
  open questions). User-only approval gate.
- ☑ `commands/plan.md` — `/wellforge:plan`: read approved spec → `plan.md` (architecture,
  data model, API contracts, test strategy w/ AC↔test mapping). Refuses non-approved specs.
- ☑ `commands/tasks.md` — `/wellforge:tasks`: derive ordered, dependency-aware task list
  (`tasks.md`) with per-task "done when" checks; bidirectional AC↔task coverage check;
  re-sync mode preserves completed tasks.
- ☑ `skills/spec-driven/SKILL.md` — conventions: directory layout (`specs/NNN-slug/`),
  status frontmatter (draft → approved → in-progress → done), drift rule
  (code change that contradicts spec ⇒ update spec first).
- ☑ Wire existing `stop-verify.sh` hook to check spec drift against this format
  (replaced old cc-sdd patterns; only fires when the spec dir already has a tasks.md).

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

- ☑ Write the 7 agent definitions (system prompt: role, inputs it expects, artifact it
  must return, what it must NOT do — e.g. PO never writes code). Designer's artifact is
  `design.md` in the spec dir (added to the spec-driven layout as optional, UI-only).
- ☑ Keep `owasp-reviewer` and `adr-writer` as specialists: architect emits
  `## ADR candidates`, QE recommends owasp passes — both invoked by the caller.
- ☑ Each agent's prompt references the spec format from Phase 1 (agents read
  `specs/NNN-slug/` as their contract; PO/architect carry the format template inline
  since subagents run non-interactively and don't auto-load skills).

Acceptance: each agent invoked standalone on a sample spec produces its artifact without
overstepping its role.

## Phase 3 — Orchestrator (Pillar 3) (1–2 days)

Goal: one entry point that routes work through the team instead of ad-hoc prompting.

- ☑ `commands/orchestrate.md` — `/wellforge:orchestrate <goal>`: classifies the request
  (feature / bugfix / refactor / infra), then drives the matching pipeline:
  - feature → PO (spec) → gate → Architect (plan) → gate → [Designer if UI] → tasks →
    FE/BE devs in parallel per task → QE verdict (max 2 fix rounds, then escalate) → done.
  - bugfix → QE (repro test) → dev (fix) → QE (verify). refactor → architect mini-plan
    w/ invariants → tasks → QE. infra → devops w/ gate on prod-like changes.
- ☑ Handoff contract: each stage's artifact is written to disk before the next stage
  starts (orchestrator passes file paths, not chat context — survives compaction);
  drift reports pause the pipeline and route to the owning agent.
- ☑ Human gates: orchestrator pauses for user approval after spec and after plan
  (AskUserQuestion), never auto-approves; it records the user's decision in frontmatter.
  Specialists dispatched at gates: adr-writer post-plan-approval, owasp-reviewer on QE
  recommendation (findings ≥ medium = defects).
- ☑ Parallelism rule: FE/BE tasks with no dependency edge run as parallel subagents.

Acceptance: `/forge:orchestrate "add CSV export to reports"` runs the full chain on a
sample project with exactly 2 human approval pauses.

## Phase 4 — Scaffolder + connection layer (Pillar 4) (3–5 days, biggest chunk)

Goal: product description in → running repo with connections out, in <30 min.

- ☑ `templates/_shared/CONTRACT.md` — binding contract: common copier questions
  (incl. hidden `generated`/`template_version`), required generated files, versioning.
- ☑ `templates/spring-kotlin-react/` v0.1.0 — extracted from
  `skills/springboot-scaffold/scripts/scaffold.sh` + react-ts-vite setup + mise skill.
  Questions: base_package, db (postgres/none), ci. Nested Java package dirs via hidden
  derived `package_path` answer (literal `/` in a templated dirname doesn't work).
- ☑ `templates/hono-react/` v0.1.0 — Hono + Drizzle (postgres/none) + react frontend.
- ☑ Both emit `.forge/manifest.json` `{ template, version, generated, answers }` and
  `.copier-answers.yml` — the upgrade contract for Phase 6.
- ☑ Both emit project-local `CLAUDE.md` + `.claude/settings.json` (pre-allowed mise/
  pnpm/mvnw commands) + `specs/README.md` — AI-ready and spec-driven on first open.
- ☑ `commands/new.md` — `/wellforge:new`: interview → stack recommendation with
  rationale (or honest "fits neither") → `uvx copier copy` → pristine scaffold commit →
  `mise run install/build/test` as acceptance bar → connections walkthrough.
- ☑ Connection layer — `skills/connections/SKILL.md` + references (github, mcp-servers,
  environments): idempotent checklists, each opening and closing with a verification
  command; incompletable steps become PENDING, never silently skipped.

Acceptance: generation verified live for both presets (defaults + non-default answers,
db=none conditionals, valid pom/package.json/manifest, no unrendered Jinja). Still
outstanding: full `mise run build/test` on a generated project (needs dependency
downloads) and CI-green (needs Phase 5 gate workflows) — both land in the Phase 7 pilot.

## Phase 5 — Quality gates (Pillar 5) (2–3 days)

Goal: the same measurable bar everywhere; CI is the enforcement point, hooks are the
fast local feedback.

- ☑ Reusable GitHub Actions (`workflow_call`) — live in `/.github/workflows/` (GitHub
  resolves `workflow_call` only from that path; `gates/` holds configs+scripts+policy):
  - `quality-node.yml`: lint (zero warnings), `typecheck`, Vitest coverage ≥ **80%**
    lines / **70%** branches (CLI-enforced), lockfile required + frozen install,
    `pnpm audit --audit-level high`, semgrep (welld rules + p/typescript).
  - `quality-jvm.yml`: ktlint (full plugin coordinates), JaCoCo lines ≥ **80%** via
    `gates/scripts/check-jacoco.py` (tested pass/fail/floor; <50-line modules skip with
    notice), osv-scanner v2, semgrep (welld rules + p/kotlin). detekt deferred to
    template v0.2 (not in pom).
- ☑ `gates/configs/semgrep/welld.yml` — central SAST rules (secrets, kotlin println,
  ts debugger). DEVIATION: eslint/ktlint configs stay template-shipped (central refs
  need an npm/maven registry — future work); they propagate via Phase 6 upgrades.
  Coverage thresholds + semgrep + audit ARE central.
- ☑ Templates call the reusable workflows pinned to `gates-v0` (wired in Phase 4;
  tag created).
- ☑ Plugin side: fixed `post-lint.sh` ktlint invocation (full plugin coordinates —
  prefix resolution was broken); hooks run the same project tasks as CI (lint/
  typecheck/compile); the QE agent runs the full gate set with numbers. Template fixes
  found by gate wiring: missing ktlint-maven-plugin in pom, missing @vitest/coverage-v8
  in both frontends, `type-check`→`typecheck` script normalization.
- ☑ Threshold changes require a PR to `gates/` (review = the only discretion point);
  thresholds live in workflow env blocks, documented in `gates/README.md`.

Acceptance: a scaffolded project with a deliberately under-tested module fails CI with
an actionable message; fixing coverage turns it green; no per-project config edits.

## Phase 6 — Lifecycle & upgrades (Pillar 6) (2–3 days)

Goal: presets evolve, fleets follow.

- ☑ STRUCTURAL: moved to copier's monorepo pattern — ONE root `copier.yml` with a
  `preset` question and templated `_subdirectory` (per-template copier.yml removed).
  Required because `copier update` resolves the template from the git repo root with
  PEP440 `vX.Y.Z` tags; per-template tags would be invisible to it. Presets release
  in lockstep; `gates-v*` is a separate tag series.
- ☑ Semver discipline documented in CONTRACT.md: patch = cosmetic, minor = additive,
  major = needs migration. First release tagged `v0.1.0`.
- ☑ `commands/upgrade.md` — `/wellforge:upgrade`: manifest+answers pre-flight, clean
  tree required, plan-of-record with changelog before running, `copier update
  --skip-answered --conflict inline`, AI conflict resolution (keep project behavior /
  adopt template structure; ambiguous → ask), gates verify, single revertable commit.
- ☑ `_migrations` convention documented in root copier.yml + CONTRACT.md (mechanical
  steps only; first entries land with the first breaking release).
- ☑ `gates/` upgrades decoupled: pinned tag bump, one-line PR — upgrade.md forbids
  bundling it into a template upgrade.
- ☑ Fleet visibility: `scripts/fleet-status.sh` — GitHub code search (or --repo-list)
  → reads each repo's `.forge/manifest.json` → table vs latest `v*` tag.

Acceptance ☑ (E2E-tested 2026-06-05): scaffold at v0.1.0 → throwaway template v0.1.1
(content change + version bump) → `copier update` → project at v0.1.1, marker file
arrived, manifest auto-bumped, **zero conflicts**. The test also CAUGHT a real design
flaw: a hidden `generated`-date answer isn't persisted by copier and produced spurious
manifest conflicts on every update — removed (commit fe78f26). Gates-green verification
on upgrade is wired into upgrade.md and lands with the Phase 7 pilot.

## Phase 7 — Pilot & rollout (1 week calendar, low effort)

- ☐ Use WellForge end-to-end on the next real project start; time-box and measure
  (setup time, gate violations caught, friction notes).
- ☐ Fix the top friction points; cut `v1.0.0` of plugin + templates + gates.
- ☐ Onboarding doc for the team (install marketplace, one happy-path walkthrough).
- ☐ Ownership: PRs to `templates/` and `gates/` require review; changelog per release.

---

## Phase 8 — Brownfield adoption (added 2026-06-05)

Goal: existing projects get the workflow + calibrated gates without pretending to be
scaffolds.

- ☑ `commands/adopt.md` — `/wellforge:adopt`: survey (read-only) → scope interview →
  AI-readiness (AGENTS.md from OBSERVED conventions, existing CLAUDE.md content
  migrated; settings merge; `.forge/adoption.json` marker — distinct from manifest,
  upgrade stays unavailable) → gates with MEASURED baseline (interface check first;
  npm/yarn and Gradle honestly unsupported → stop and report) → connections → single
  revertable commit. Adds files only; never rewrites existing code/config.
- ☑ Gates ratchet: both workflows accept `coverage-lines-baseline` (+ branches on
  node), 0 = central thresholds; non-zero = per-project measured minimum, raise-only
  via PR, gap-to-target notice on every run. Tagged `gates-v1` (gates-v0 unchanged
  for existing scaffolds).
- ☐ Pilot on a real brownfield repo (pairs with Phase 7).

## Phase 9 — Eval harness / LM-judge (added 2026-06-23)

Goal: close the gap analysis P1 — the non-deterministic verification half (rubric +
LM-judge), so WellForge verifies *how good*, not just *does it pass*.

- ☑ Central rubric `gates/configs/eval-rubric.yml` (weighted dims, floors, pass ≥ 80;
  PR-governed; per-feature `eval.md` raise-only overrides).
- ☑ `evaluator` LM-judge agent (adversarial, evidence-cited; distinct from QE) →
  `eval-report.md`.
- ☑ `/wellforge:eval` command; passing eval = gate into `done` (lifecycle, status,
  implement, orchestrate all wired).
- ☑ Opt-in CI: `quality-eval.yml@gates-v2` + `run-eval.py` (tested offline:
  pass/fail-by-total/fail-by-floor).
- ☑ P2 observability (plugin v2.2.0): `.forge/runs/` run traces (schema wellforge-run/v1)
  written by implement/orchestrate/eval; SubagentStop token-event hook + run-report.py
  cost estimates (central `config/model-pricing.yml`); drift telemetry in traces;
  `/wellforge:status` observability view; evaluator trajectory now reads real traces.
- ☑ P3 intelligent model routing (plugin v2.3.0): central `config/model-routing.yml`
  (frontier/mid/cheap tiers, per-agent assignment + rationale); every agent's frontmatter
  model set to its tier; `check-routing.py` drift guard; CI/in-session judge tiering
  documented. All three gap-analysis material gaps (P1 evals, P2 observability, P3 routing)
  now closed.

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
