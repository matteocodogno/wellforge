# WellForge — Implementation Plan

Status legend: ☐ todo · ◐ in progress · ☑ done

---


## Carried over from the review artifacts (2026-09-21)

`docs/improvement-prompts.md` and `docs/cli-improvement-prompts.md` were exhausted review
documents and were deleted in `63d107e`. Everything in them had shipped **except** these
two, which the deletion took with it — recorded here so they exist somewhere that is read.

- ☐ **Plugin evals.** `claude plugin eval` can run a suite against the plugin's own
  commands and skills (see the `claude-code-guide` agent for the current JSON/report shape,
  sandbox and CI story). WellForge has regression matrices for every *script* and hook but
  nothing that exercises a command end to end as a user would invoke it, so a command whose
  prose stops making sense fails silently — the failure mode this repo keeps rediscovering.
- ☐ **The `jq` / AskUserQuestion hook item.** Hook scripts exit 0 when `jq` is missing
  (`post-spec-guard.sh` says so explicitly), which is correct as a fallback and invisible as
  a state: a machine without `jq` runs with every lifecycle guard silently disabled.
  `/wellforge:doctor` reports `jq` in its toolchain table, but nothing surfaces it at the
  moment a guard declines to run. Decide between a one-time session-start notice and
  leaving it to doctor — and if the answer is "leave it", write that down, because the
  question has now been asked twice.


## Phase 0 — Foundations & decisions (½ day)

Goal: lock the decisions everything else depends on.

- ☑ Vehicle: **hybrid** — Claude Code plugin + Copier templates + shared CI gates.
  A plugin alone cannot version generated projects or enforce gates in CI.
- ☑ Spec framework: **thin in-house layer** (spec → plan → tasks), spec-kit-style,
  packaged as plugin commands. Rationale vs. alternatives tried:
  - *BMAD*: powerful but heavyweight; too much ceremony for typical WellForge project size.
  - *superpowers*: great skill-authoring patterns — borrow the style, not the framework.
  - *Kiro*: good spec UX but tied to its own IDE/runtime.
  - *cc-sdd / spec-kit*: closest to what we want — adopt the spec→plan→tasks shape,
    but own the prompts so they encode WellForge conventions and don't churn under us.
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
  `skills/springboot-scaffold/scripts/scaffold.sh` (deleted 2026-09-20 — see Phase 19) +
  react-ts-vite setup + mise skill.
  Questions: base_package, db (postgres/none), ci. Nested Java package dirs via hidden
  derived `package_path` answer (literal `/` in a templated dirname doesn't work).
- ☑ `templates/hono-react/` v0.1.0 — Hono + Drizzle (postgres/none) + react frontend.
- ☑ `templates/pulumi-gcp-ts/` (added template v0.7.0) — Pulumi Infrastructure-as-Code
  (TypeScript) on GCP: per-environment stacks, typed config, a `SecureBucket`
  ComponentResource, a CrossGuard policy pack, and unit tests on Pulumi's mock runtime.
  Questions: gcp_project, gcp_region. Reuses the `quality-node` gate (single `infra` dir).
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
    `pnpm audit --audit-level high`, semgrep (WellForge rules + p/typescript).
  - `quality-jvm.yml`: ktlint (full plugin coordinates), JaCoCo lines ≥ **80%** via
    `gates/scripts/check-jacoco.py` (tested pass/fail/floor; <50-line modules skip with
    notice), osv-scanner v2, semgrep (WellForge rules + p/kotlin). detekt deferred to
    template v0.2 (not in pom).
- ☑ `gates/configs/semgrep/wellforge.yml` — central SAST rules (secrets, kotlin println,
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

**2026-09-20 — the first real `mise run install` on a generated project, and it failed
three times over.** Running the outstanding pilot item instead of reasoning about it:

- ☑ **Aggregate tasks never resolved.** Both app presets declared
  `depends = ["backend:install", …]`, but mise merges config walking UP from the cwd, so the
  root never sees `backend/mise.toml`'s tasks — `mise ERROR task not found: backend:install`
  on mise 2026.9.0. `//` addressing and `experimental_monorepo_root` do not exist in that
  version (the setting warns `unknown field` and is ignored, which is why the presets' own
  `experimental = true` looked like it was doing something). Fixed with root pointer tasks
  (`dir = "backend"`, `run = "mise run install"`), which keeps one definition per task.
- ☑ **`./mvnw` in every backend task, and no wrapper is shipped** — the next error after the
  first fix was `./mvnw: No such file or directory`. mise provides `maven 3.9.9`, so the
  command is `mvn`. Eight tasks corrected.
- ☑ **`ktlintCheck`/`ktlintFormat` are Gradle task names** in `scaffold.sh` and the `mise`
  skill (the shipped template already had the Maven goal right, so this hit hand-scaffolded
  services and anyone following the skill).
- ☑ **`jooq.version` pinned to 3.19.18, which was never published** (jooq-bom → HTTP 404).
  3.19.38 is the current 3.19.x and resolves.
- ☑ **Fixed in `v0.10.0`** (was: *Still failing*): `spring-modulith-starter-jooq` has
  never been published in ANY Spring Modulith release — not a missing managed version, a
  nonexistent artifact, so the generated POM did not parse at all. The preset uses
  `spring-modulith-starter-jdbc`, which is what backs the event publication registry;
  the application's own data access is still jOOQ. See `docs/TEMPLATE-MIGRATIONS.md`
  → v0.10.2 for the `EVENT_PUBLICATION` schema initialisation this then exposed.
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
- ☑ **Rubric reachable from a scaffolded project** (plugin `2.27.1`, fixed 2026-09-20). The
  whole eval half was wellforge-only and nobody noticed, because it was only ever exercised
  *here*: the evaluator, `/wellforge:eval` and `orchestrate` all read
  `gates/configs/eval-rubric.yml` relative to the project, and a scaffolded project has no
  `gates/` — gates are called by CI, never copied. So `/wellforge:eval` could not run in any
  generated project, and since `production`'s done gate requires an eval PASS, no production
  feature could close. Fixed by a byte-identical mirror in the plugin
  (`config/eval-rubric.yml`, emitted by both adapters too) plus a documented resolution order
  in the evaluator — project `gates/` → CI's `.wellforge-gates/` checkout → tool-bundled copy
  — and a `rubric-sync` CI job that fails if the mirror drifts from the central rubric. No
  template cut: the fix ships with the plugin, so it reaches existing projects on upgrade.
  A reminder that "☑ wired" means wired *in this repo* until the pilot proves otherwise.
- ☑ P2 observability (plugin v2.2.0): `.forge/runs/` run traces (schema wellforge-run/v1)
  written by implement/orchestrate/eval; SubagentStop token-event hook + run-report.py
  cost estimates (central `config/model-pricing.yml`); drift telemetry in traces;
  `/wellforge:status` observability view; evaluator trajectory now reads real traces.
- ☑ P3 intelligent model routing (plugin v2.3.0): central `config/model-routing.yml`
  (frontier/mid/cheap tiers, per-agent assignment + rationale); every agent's frontmatter
  model set to its tier; `check-routing.py` drift guard; CI/in-session judge tiering
  documented. All three gap-analysis material gaps (P1 evals, P2 observability, P3 routing)
  now closed.

## Phase 10 — Rigor tiers (added 2026-06-25)

Goal: match ceremony to stakes — a velocity escape hatch so feasibility work isn't forced
through full production rigor. **Full plan + per-phase detail: [PLAN-rigor-tiers.md](PLAN-rigor-tiers.md).**

- ☑ A — workflow parametrization (plugin v2.7.0): `rigor-tiers` skill, `/wellforge:spike`
  (main-loop fast lane), `--mode` on orchestrate/implement, security floor.
- ☑ B — scaffold dimension (gates-v5, template v0.4.0): `rigor` copier question → manifest;
  tier-conditional CI (spike = security-floor + build; mvp = coverage advisory); README/AGENTS badge.
- ☑ C — graduation (plugin v2.9.0): `/wellforge:promote` pays the deferred debt (brief→spec→plan,
  backfill tests, blocking gates, eval); `/wellforge:status` shows tier + staleness nag.

Defer-don't-lower: a lower tier is tracked debt, raised only via promote, production only on
an eval PASS. Self-CI (`.github/workflows/ci.yml`) added alongside.

**Follow-up fix** (plugin `2.27.2`, 2026-09-20): the `mvp` tier was defined but its path was
blocked. `/wellforge:tasks` and `/wellforge:implement` both gated on an **approved plan.md**
with no tier exception, while `orchestrate`'s mvp pipeline, `promote --to mvp` and
`/wellforge:status` all route mvp features — which have no plan.md *by design* — into exactly
those commands. Followed literally, every mvp feature dead-ended, and nothing in the flow
would ever produce the plan they were waiting for. Both gates are now tier-aware (plan at
`production`, spec at `mvp`, `spike` redirected), the spec-driven skill's absolute "MUST
refuse unless plan.md is approved" bullet is qualified, and the folded-away plan has a
defined home: a `## Architecture notes` section in tasks.md that `orchestrate` already
assumed existed but no format defined. The lesson is the same one Phase 9's rubric fix
taught: a tier that is never exercised end-to-end is a tier that is only *written*.

**Follow-up fix** (plugin `2.27.4`, 2026-09-20): the `done` transition was set in four
places while `done.md` called itself "the single guarded place". `spike.md` flipped it
inline, `promote.md` flipped it **without checking every task was ticked**,
`orchestrate.md`'s mvp close flipped it **without the `done:` date** (its production close
re-implemented the gate correctly, which is how the drift stayed invisible), and `eval.md`
contradicted itself — Step 4 said it doesn't flip the status, its hard rules said it produces
"on the user's confirmation, the spec `done` status". Fixed by making `done.md` the only
implementation and a callable procedure: all three commands now run it, it re-verifies
against the artifacts on disk rather than the caller's recollection, it always stamps
`done: <today>`, and a promoted feature is re-gated at its NEW tier instead of inheriting the
mvp close. The spec-driven skill's "(or `/wellforge:orchestrate`'s close step, same gate)"
parenthetical — which sanctioned the second copy — is gone. Same species as the two fixes
above it: the gate was right in the place that was read, wrong in the places that ran.

## Phase 11 — SDLC extension & hardening (added 2026-06-29)

Goal: close outer-loop gaps and harden the agent system, off the back of an "is this all of
the SDLC?" review (deploy/operate still open; see FEATURES for the honest coverage map).

- ☑ Release management (template v0.5.0, plugin v2.13.0): `/wellforge:release` + per-preset
  `.release-it.json` — version bump + `CHANGELOG.md` from Conventional Commits via **release-it**
  (`@release-it/conventional-changelog` + `@release-it/bumper`); brownfield support in `/wellforge:adopt`.
- ☑ Incremental adoption (plugin v2.15.0): re-run `/wellforge:adopt` to add a skipped layer
  (add-layers mode; merges `adoption.json`, never regenerates the core).
- ☑ Tier-gated effort cue (plugin v2.16.0): a tool-neutral per-tier "how hard to think"
  directive (spike minimal / mvp moderate / production full) — no per-agent config.
- ☑ Agent review — Wave 1 (v2.16.1): stack/path/naming fixes (owasp jOOQ/Drizzle + Hono,
  non-interactive; devops gates path; adr-writer de-cc-sdd). Wave 2 (v2.17.0): defect triage
  to the true owner, proactive security scheduling, dev ADR candidates. Wave 3 (v2.17.1):
  backup-hook de-cc-sdd, `.claude/transcripts/` gitignore (template v0.5.1), designer
  `disallowedTools:[Edit]`, observability schema sync.
- ☑ MIT `LICENSE`; README revamp (Forgey mascot); docs sync.

**Follow-up fix** (plugin `2.27.5`, 2026-09-20): two stack skills told agents to do what the
plugin's own hook blocks. `hono-ts-backend` said `cp .env.example .env` and `react-ts-vite`
listed `.env.production` as the home for "prod secrets", while `pre-bash-guard.sh` refuses any
command mentioning a dotenv file and the `connections` skill names `.mise.local.toml` as the
convention. An agent following the stack skill got stopped mid-setup by its own toolchain.
The Vite half was a security bug, not just a clash: `VITE_`-prefixed values are statically
inlined into the client bundle, so a "secret" there is served to every visitor. Both skills
now route real values to `.mise.local.toml` (injected by mise, so `process.env` and the Zod
schema work unchanged), keep `.env.example` as the committed *manifest* of variable names, and
cite `connections/references/environments.md` as the authority; the `mise` skill's
"`.mise.local.toml` **or** a gitignored `.env.local`" alternative is gone for the same reason.
Also fixes the `docker run --env-file` line, which had the same conflict.

## Phase 12 — Design tooling & template reuse (added 2026-07-05)

Goal: enrich the design stage (Pillar 2) with real mockups, and close the brownfield loop
(Pillars 4/6 + Phase 8) so an adopted project can seed the team's next scaffold.

- ☑ Visual companion for the designer (commit 63fc8cf): opt-in `--visual` flag on
  `/wellforge:design` starts a browser-based companion the designer uses to show mockups,
  wireframes, and side-by-side layout comparisons and read back the user's clicks — instead
  of describing UI in text. `design.md` stays the deliverable; mockups persist as evidence
  under `.forge/design/<feature>/`. Server adapted (MIT) from the superpowers `brainstorming`
  skill — rebranded, telemetry/logo removed, `THIRD_PARTY_LICENSE` retained; adds design-system
  `--theme` overlays (mantine/mui/shadcn/wireframe) so mockups match the project's real
  component library, and per-feature `--session-name` persistence. Triple-gated: flag-enabled,
  interactive-only (never headless `/wellforge:orchestrate`), never the `spike` tier. New
  `visual-companion` skill + designer/command wiring; both template `.gitignore`s ignore
  `.forge/design/`. Verified: E2E serve + themed frame + helper injection + click-event
  capture; all four themes inject; no-key requests 403; mockups persist.
- ☑ Stack profile + gap check, and org-internal template extraction (commit 2935355):
  **(#1)** `/wellforge:adopt` Stage 0 now writes `.forge/stack-profile.json` (structured
  fingerprint) and classifies the project against the shipped presets — `covered` / `partial`
  / `novel` + closest preset + recommendation (informs only, never blocks). **(#2)** opt-in
  extraction reverses a project into a CONTRACT-compliant Copier template the **org owns**, at
  a user-chosen destination, so the team's next service starts from its own proven stack.
  Hard safety gate first: skeleton-only (no domain code), secret scrub, IP/license check, and
  a required `copier copy --defaults` render verification. New `template-extraction` skill +
  `/wellforge:extract-template` command; adopt wires Stage 0 profile, a Stage 1 opt-in layer,
  Stage 5b extraction, and `adoption.json`. Scope-bounded: never writes into the source project
  or the WellForge repo, and **never opens a PR to the WellForge catalog** — upstream
  contribution stays a separate, human-curated decision (deliberately out of scope).

Honest status: both are prompt/skill-authored (no runtime tests beyond the visual-companion
server smoke test and the extraction's `--defaults` render check). Live validation is pending —
a real `/wellforge:design --visual` session and a `/wellforge:extract-template` run on a
brownfield repo (pairs with the Phase 7 pilot). Shipped on the plugin v2.19.x line; plugin.json
was not bumped in those two commits — the version caught up at the Phase 14 release (`2.22.0`),
so both are carried by every plugin version since.

**Follow-up fix** (plugin `2.27.3`, 2026-09-20): `pulumi-gcp-ts` shipped as a template but was
never wired into the front door. `/wellforge:new` hard-coded "the only two — do not invent
others", and its "fits neither → stop, don't force a preset" rule meant an infra request was
actively refused rather than routed to the preset built for it; `template-extraction`'s
gap-check had the same two-preset assumption plus a backend/frontend-shaped heuristic that
lands an IaC repo on "novel" because both halves are *missing*. Fixed: three-preset table
with `pulumi-gcp-ts` framed as orthogonal (it answers "what runs this"), an infrastructure
option in the Stage 1 interview so the path is discoverable at all, the preset-conditional
answer set (`gcp_project`/`gcp_region`, no `db`), and an is-it-an-application-at-all branch
in the gap check. The durable half: both files now name the root `copier.yml`'s `preset:`
choices as the authoritative list, so a fourth preset strands nothing.

## Phase 13 — Loop engineering: parallel worktree isolation (added 2026-07-06)

Motivated by O'Reilly's "loop engineering" (five components: automations, worktrees, skills,
plugins/connectors, subagents). Audit found WellForge already ships four — skills, verifying
subagents, connectors, external state — plus the article's "stay the engineer" spine (human
gates + rigor tiers). Two genuine gaps: **worktree parallel-safety** (this phase) and
**scheduled "heartbeat" automations** (Phase 14, below).

> **Loop-engineering initiative COMPLETE (2026-07-06).** All five components are in place: the two
> gaps are closed — worktree parallel-safety (Phase 13, plugin v2.21.0) and heartbeat automations
> (Phase 14, `gates-v6`/`gates-v7` + template `v0.6.0` + plugin `2.22.0`). Remaining work is **live
> field validation only** (a real scheduled run; agentic routines wired to org cron), which pairs
> with the Phase 7 pilot — not additional build.

- ☑ Worktree-isolated parallel dispatch (plugin v2.21.0): `implement` Step 3 and
  `orchestrate` (feature + mvp implementation) now isolate any batch of **≥2 dependency-
  independent dev agents** in a git worktree (`isolation: "worktree"`) so parallel FE/BE
  edits can't collide in one working tree. Protocol: each parallel agent commits its code on
  its own branch and **does not touch `tasks.md`** (checkbox reconciled centrally, killing the
  one guaranteed conflict); the main loop merges each reported branch into the feature branch,
  reconciles all checkboxes in one commit, and prunes the worktrees. A **merge conflict is a
  "collision"** — two tasks the DAG called independent touched the same file, so the edge was
  wrong: surfaced like drift, resolved by adding the missing `deps:` + `/wellforge:tasks`
  re-sync, never auto-resolved. Solo/sequential batches stay in the main tree (no overhead).
  Wired: `settings-snippet.jsonc` sets `worktree.baseRef: "head"` (worktrees branch from HEAD,
  not the remote default); observability schema gains per-agent `worktree` + `collision_events`;
  CLAUDE.md conventions record the rule.

Honest status: prompt-authored, **smoke-tested 2026-07-06** (not yet exercised through a real
`/wellforge:implement` feature). The commit **flow-back** from an isolated subagent worktree is
not officially documented, so it was verified live in two layers: (A) the reconciliation logic
in a throwaway repo — two worktrees with disjoint edits merge clean + central checkbox reconcile,
and two worktrees editing the same file produce a detected collision (merge aborts, tree left
clean); (B) the real harness — two subagents dispatched in parallel with `isolation: "worktree"`,
each committing in its own worktree, then merged back into an isolated integration branch, clean.
Two findings from (B), now baked into the protocol: the dispatch result **surfaces each isolated
agent's `worktreeBranch`/`worktreePath` in its metadata** (so the parent needn't rely on the
agent self-reporting its branch — that's the portable fallback), and merge-back must use git's
**default merge message** (`--no-edit`) because the Conventional-Commits `commit-msg` hook rejects
a custom `-m "merge …"`. A sequential main-tree **fallback** ships for when isolation is
unavailable. Remaining validation — a real parallel feature batch end-to-end — pairs with the
Phase 7 pilot.

Deferred (not built): scheduled "heartbeat" automations — `on: schedule` gate/dependency audits
and a fleet-drift triage agent that notices when a project falls behind the latest template tag.
The article's automations component; drafted below as **Phase 14** (starts after the Phase 7
pilot proves the core loop).

**Follow-up fix** (plugin `2.27.7`, 2026-09-20): `stop-verify.sh`, the mechanical half of the
drift rule, had been blind since it was written. It used a bare `git diff --name-only`, which
reports **unstaged changes only** — and every dev agent's standing instruction is to commit on
completion, so the moment an agent finished, its work left the hook's field of view. The drift
check and both compile checks then passed by seeing nothing, which is indistinguishable from
passing. Three more defects in the same file: `./mvnw clean compile` on every Stop with no
`timeout` in `hooks.json` (the default budget is 60s — a mid-size reactor blows through it, the
hook is killed, and a killed hook exits non-2 and silently never blocks: the expensive check was
also the least likely to run); `${CHANGED_KOTLIN}${CHANGED_POM}` concatenated without a
separator, so the "first changed file" could be `Foo.ktpom.xml`; and only the Maven root holding
that first file was ever compiled, leaving a second reactor unchecked. Now: changed set =
merge-base ∪ staged ∪ unstaged ∪ untracked, `clean` dropped, a per-root wall-clock budget that
**reports** `NOT verified (advisory)` instead of dying quietly, `timeout: 300` in `hooks.json`,
and every Maven root compiled. Backed by `tests/stop-verify.test.sh` (13 cases, wired into
ci.yml) — verified meaningful by running it against the pre-fix hook, which fails 6 of them.

## Phase 14 — Loop engineering: heartbeat automations (drafted + shipped 2026-07-06 ☑)

Goal: close the last of the five "loop engineering" components — **automations (the heartbeat)**:
scheduled tasks that do discovery + triage on a cadence and **surface work for a human**, instead
of everything being pull-only (a person typing `/wellforge:*`). Extends Pillar 5 (gates run on a
schedule, not only at PR time) and Pillar 6 (a project/fleet *notices* it has drifted behind the
template — today the upgrade machinery exists but nothing watches). Prereq: Phase 7 pilot, so we
tune cadence/thresholds against a real project before automating noise.

**North-star principle — surface, never auto-ship.** Every heartbeat opens/updates an issue,
posts a digest, or drafts a *PR gated on human review*. None merges, deploys, or self-approves.
This is the article's own warning ("stay the engineer") and WellForge's existing gate philosophy —
a heartbeat is discovery + triage, not autonomous shipping. Same defer-don't-lower spine: findings
are tracked debt, a human decides.

Two vehicles, matching the architecture table — deterministic checks as GitHub Actions, judgment
as scheduled agents:

- ☑ **14a — Scheduled gate heartbeat** (Pillar 5, deterministic → GitHub Actions, built
  2026-07-06). The scheduled caller **re-uses the existing `quality-<stack>.yml` gates directly**
  (zero gate-logic duplication) — so it runs the full dependency/CVE audit + SAST + coverage on a
  cadence — and adds ONE new reusable workflow, `heartbeat-report.yml`, that manages a **single
  deduplicated tracking issue**: opens on first failure, updates in place each failing run (never a
  new issue per cycle), closes with a comment when green. Opt-in via copier answers `heartbeat`
  (default true) + `heartbeat_cron` (default `0 6 * * 1`, weekly), recorded in the manifest;
  generated only for `ci == github` AND `rigor != spike` (copier `{% if %}` filename idiom).
  Files: reusable `.github/workflows/heartbeat-report.yml`; `heartbeat.yml.jinja` in both presets;
  copier answers + `gates_ref` default `gates-v5 → gates-v6`; manifest + CONTRACT + gates/README +
  preset README. Verified: renders for spring (backend JVM) and hono (backend Node) defaults,
  correctly **absent** for `rigor=spike`; all three workflow files are valid YAML. **Released**:
  `heartbeat-report.yml` shipped at **`gates-v6`** (tagged + pushed). Full E2E (a scheduled run
  opens/updates the issue) still needs a real generated repo → pairs with the Phase 7 pilot. Chose
  "all three checks + weekly" per user; coverage runs too since reusing the whole gate is more DRY
  than a bespoke subset.
- ☑ **14c — The heartbeat was actually EXERCISED** (2026-09-22). 14a and 14b were both
  released and neither had ever run: `template-drift.yml` and `heartbeat-report.yml` are
  `workflow_call`-only, nothing in CI calls them, and no generated project had reached a
  scheduled cycle — so the first real run would have been the test, in somebody else's
  repository, of a report job whose job is to CLOSE issues. Added `workflow_dispatch` to
  `template-drift.yml` and ran it against this repo:

  **https://github.com/matteocodogno/wellforge/actions/runs/35690889113** — green.

  What it proves, which is the part that matters:
  - `check` took the "no `.forge/manifest.json` — not a WellForge scaffold" branch and
    emitted `behind=false`, as intended for a non-scaffold.
  - `report` ran and reached `Heartbeat green and no open tracking issue — nothing to do.`
    That is heartbeat-report's **no-op branch** — the one that decides whether to close a
    tracking issue, and the branch that was wrong until `gates-v13` (a crashed `check`
    produced no outputs, `'' == 'true'` was false, and the drift issue was closed as
    "green again").
  - `heartbeat-failed` was correctly **skipped**, because `check` succeeded.
  - **`uses: ./.github/workflows/heartbeat-report.yml` resolved.** The local-path form was
    questioned in review on the theory that a consumer's runner resolves `./` against the
    consumer repo; it does not — GitHub resolves it against the repository containing the
    calling workflow, at the same commit. Keeping `./` is also the only maintainable
    choice, because `uses:` accepts no expressions and a fully-qualified form would need a
    hardcoded `@gates-vN` bumped by hand every release.

  Still not covered: the failing path (an actually-behind manifest opening an issue) and a
  real scheduled trigger in a generated repo. Both need the Phase 7 pilot, as 14a already
  says.

- ☑ **14b — Template-drift heartbeat** (Pillar 6 — the WellForge-native standout, deterministic,
  built 2026-07-06). New reusable `template-drift.yml`: reads `.forge/manifest.json`, resolves the
  latest `vX.Y.Z` of the source repo (`git ls-remote`, version-aware count), and files/updates ONE
  deduplicated *"N releases behind → `/wellforge:upgrade`"* issue (label `template-drift`) — closing
  it automatically when the project catches up. Reuses the 14a `heartbeat-report.yml` (generalised
  with a `body` input). Wired as a `template-drift` job in both heartbeat callers. Verified: version
  count (0.4.0→2 behind, etc.), heredoc body + `GITHUB_OUTPUT` multiline format, renders in both
  presets. Ships at **`gates-v7`**. Draft-PR stretch deferred.
- ☑ **14b — Fleet heartbeat** (org-wide triage, built 2026-07-06). `scripts/fleet-triage.sh` extends
  `fleet-status.sh`: per repo it reports template drift **and** gate health (latest default-branch CI
  conclusion), grouped by what needs attention + a summary; degrades per-repo, never aborts. The
  scheduled-routine recipe (post to one rolling issue, `gh`-token auth in headless runs, cost bound,
  surface-never-ship) is in `scripts/README.md`. Not a live cron — scheduling is the org's infra.
- ☑ **14b — Spec-health heartbeat** (Pillar 3 — trajectory triage, built 2026-07-06). New
  `/wellforge:triage` command (also the scheduled agent): reads `specs/` + `.forge/runs/` and
  surfaces three deterministic signals — stale `in-progress`, unresolved drift (`drift_open`), and
  passed-QE-never-eval'd (production) — plus lower-tier debt. Read-only digest; the scheduled-routine
  wiring + caveats are in the command. Surface, never fix.
- ☑ **14b — `heartbeat` skill** — canonical conventions for all four heartbeats: surface-never-ship,
  one-deduplicated-issue-per-concern, the deterministic-vs-agentic split, off-for-spike, the cost
  bound + `gh`-auth-degrades rule for agentic ones, cadence, and the run-trace format.

Sequencing inside the phase: shipped the **deterministic GitHub Actions heartbeats first** (gate +
template-drift — cheap, no token cost), then the **agentic** fleet/spec-health triage as runnable
pieces + scheduling recipes.

Honest status: **shipped 2026-07-06 (☑).** Released as `gates-v6` (gate reporter), `gates-v7`
(template-drift + generic reporter body), template **`v0.6.0`** (so `/wellforge:new` scaffolds and
`/wellforge:upgrade` carry the heartbeat callers), and plugin **`2.22.0`** (`/wellforge:triage` +
`heartbeat` skill). Repo self-CI green, including a Node-24 action bump (`checkout@v5`,
`setup-uv@v7`) done in passing. Two things remain, both **deliberately deferred to the Phase 7
pilot**, not gaps in the build: (1) **live E2E** — a real scheduled run firing and opening/updating
an issue; render + logic are verified, but no cron has fired in a generated repo yet. (2) **agentic
scheduling** — fleet + spec-health ship as the runnable data step (`fleet-triage.sh`) + command
(`/wellforge:triage`) + routine recipes, but **live cron is the org's infrastructure, deliberately
not auto-enabled**; the Claude Code routine must degrade to `gh`/API auth in headless runs
(interactive MCP servers may be absent), and cadence/thresholds still want the pilot's real signal.
14b was built ahead of the pilot at the user's request; the pilot confirms whether the agentic layer
earns its keep over the deterministic heartbeats alone.

**Follow-up fix** (plugin `2.28.0`, 2026-09-20): the guard hooks were tested by attack rather
than by reading, and both halves failed. Six bash rules had bypasses — `push -f`, `push origin
+main`, `reset --hard <ref>` (only `HEAD~2..9` was covered), `branch -D`, `rm` with flags in
separate tokens, `DROP TABLE` without a trailing semicolon — and `.envrc`, direnv's file and the
same secret class, was invisible while `.env` was blocked. All six now block, with
`--force-with-lease`, `branch -d` and `rm -rf <path>` still allowed because the worktree and
linear-history workflows depend on them. The structural finding is bigger than the six: the
guard only ever covered **Bash**, because it matches command text. `Write` could create a
secret file, `Read` could read one — the tools an agent actually reaches for. New
`pre-file-guard.sh` (PreToolUse on `Read|Write|Edit|MultiEdit|NotebookEdit`) inspects the
`file_path` *parameter*, so it is exact where the text rule can only guess; `.mise.local.toml`
is deliberately write-allowed and read-blocked, since it is the sanctioned secret store the
setup flow writes but whose values must not reach the transcript. Regression matrices for both
(53 + 48 cases, wired into ci.yml), verified meaningful against the pre-fix guard: 13 fail. The
text-only limits — false positives on any command *mentioning* a protected name, and evadability
by anyone actually trying — are now documented in the plugin README rather than being folklore.

**Follow-up fix** (plugin `2.28.1`, 2026-09-20): the cost half of observability was wrong in
three ways. `trace-subagent.sh` recorded tokens and model but no **agent identity**, so
`run-report.py` could only attribute events by time window — and a parallel batch has
overlapping windows by construction, so each run counted the other's tokens. Measured on a
two-run fixture: both runs reported 1500/2700 tok and $0.045, against a true 1000/2000 +
500/700 split; the estimate doubled, silently, exactly where a run is most expensive. The
hook now records `agent_type`/`agent_id`/`session_id` when the harness exposes them, and
attribution matches window→identity, leaving genuinely ambiguous events **unattributed and
reported** rather than counted twice. Second, the pricing table existed twice — in
`config/model-pricing.yml` and as `_FALLBACK_PRICING` in the script, "kept in sync" by
comment. Both had drifted years stale (Opus 15/75, Haiku 0.80/4.00). The embedded copy is
deleted; a missing table now reports *no* cost instead of a confident wrong one. Third, the
rates are refreshed from the `claude-api` skill's table (Opus 5 $5/$25, Sonnet 5 $2/$10,
Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5, Fable $10/$50) and matched **longest-key-first**, since a
bare `sonnet` key silently charged Sonnet 5 at 4.6's price. 16-case regression matrix wired
into ci.yml. The lesson repeats: a wrong number still prints, so nothing failed.

## Phase 15 — Craft skills: visual direction & debugging discipline (added 2026-08-11)

Goal: two gaps that surfaced from comparing WellForge's skill set against public skill
collections. Both are **discipline** skills (like `rigor-tiers`), not stack conventions —
they govern *how* work is done rather than what a stack looks like.

- ☑ **`frontend-design`** (plugin `2.24.0`, commit 48c61f7). Everything else in the plugin
  pushes toward sameness — reuse the library, match the surrounding code, never add a second
  UI library — which is right for internal apps and wrong when the surface *is* the product.
  This is the gated exception. A **surface-class gate** runs first: a feature inside an
  existing design system → the system wins (the common case, and the skill says so rather
  than implying a shortfall); a new public-facing area → inherit type + neutrals, spend ONE
  new axis; a greenfield first UI / prototype / demo → full two-pass direction. Produces a
  token system (color / type / layout / signature) as an optional `## Visual direction`
  section in `design.md`, which frontend-dev implements as **theme tokens**, never ad-hoc
  CSS. Anti-default calibration names the three AI-design clichés plus **our own fourth**
  (untouched Mantine + slate/indigo Tailwind + `rounded-md` + a gradient stat row).
  Checkable floor: computed contrast (4.5:1 / 3:1), visible focus, reduced motion by media
  query, 360px — plus a font-delivery rule (no CDN `<link>` under a CSP or an offline build).
  Wired into designer (artifact template + when to load), frontend-dev (binding when
  present), `/wellforge:design` step 4, and the Copilot adapter as a command-scoped skill.
- ☑ **`systematic-debugging`** (plugin `2.25.0`, commit e9cbdb8). The `bugfix` pipeline
  covered the *workflow* (QE repro → dev fix → QE verify) but nothing covered the
  *investigation*, and it only existed inside `/wellforge:orchestrate` — while most debugging
  happens in the main loop, in a spike, or inside a dev agent whose own tests go red. Adds
  the **iron law** (no fix without a stated root cause, at every tier including spike), the
  **fix-attempt counter** (3 failures on one symptom = architecture signal → routed through
  the existing drift rule to the architect, never a fourth patch; in a spike it *is* the
  finding), and **never-make-the-symptom-disappear**, which extends the dev agents' existing
  "don't weaken the gate" rule to raised timeouts, unexplained retries, catch-and-log,
  `.skip`/`@Disabled` and lowered thresholds. Phase 4 delegates to `quality-engineer`'s
  bug-reproduction mode rather than restating it, keeping one source of truth for the repro
  rule. The counter **composes** with `/wellforge:implement`'s 2-round QE loop — whichever
  trips first, stops. Wired into both dev agents, QE, the bugfix pipeline, implement's
  escalation loop, and spike's advisory-gate step; Copilot gets the iron law + counter
  repo-wide in `copilot-instructions.md` (no path glob fits an "anything goes red" trigger).

Honest status: both are prompt-authored, verified only by re-running the Copilot adapter
(both land in `.github/wf-skills/`). Neither has runtime teeth — in particular the attempt
counter is a discipline the model keeps, not something a hook enforces. The enforceable
version would be a `PostToolUse` hook counting consecutive edit→failed-test cycles on the
same file; deliberately not built yet. Live validation pairs with the Phase 7 pilot.

**Follow-up fix** (plugin `2.29.0`, 2026-09-20): five agent definitions disagreed with the
commands that spawn them — the same authority-vs-caller split as the earlier fixes, but
inside the agent layer. `designer` claimed `disallowedTools: [Edit]` enforced "structurally"
that it cannot touch code, while inheriting Write and Bash (both adapters already printed
"can't deny 'edit' — relying on the prompt"; only the Claude agent file claimed otherwise) —
now `NotebookEdit` is denied too, the false claim is replaced by an explicit *Files you may
write* contract, and the frontmatter says plainly what is and is not sealed. `quality-engineer`
said "a single ✗ means FAIL, no pass with remarks" while three commands invoke it "in advisory
mode" that did not exist — it is now a defined mode (blocking: SAST-high, lint, typecheck,
security floor; advisory: coverage, reported as a gap and never ✗; the verdict line names the
mode), with the security floor non-advisory at every tier. Both dev agents said "check the box
in tasks.md and commit", the one thing worktree isolation forbids, with the override living
only in the dispatch prompt — the agents now branch on the linked-worktree test themselves,
because an agent that behaves only when reminded is a collision waiting for the dispatch that
forgets. `product-owner`'s spec template had no `rigor:` field that `/wellforge:orchestrate`
expects it to set. `adr-writer` described itself as firing automatically and "offering" updates
— neither possible non-interactively, so the AGENTS.md line was simply never written; it now
appends it itself (and gained the `Edit` it needed to), while the design.md reference is
proposed to the caller rather than written into another agent's artifact.

## Phase 16 — Parallel-safety, round 2: the pilot's field findings (added 2026-08-16)

The first four defects the **Phase 7 pilot** found by running spec→plan→tasks→orchestrate on a
real project (Byline). All four are WellForge-level — they recur on every project and every
batch, not just that one. Phase 13 built worktree isolation and smoke-tested it; this phase is
what a *real* parallel feature batch taught us that the smoke test could not.

Three of the four are the same underlying error: **a worktree isolates the checkout and nothing
else**, and we had reasoned as though it isolated the environment.

- ☑ **`worktree-isolation` skill** (plugin `2.26.0`) — the protocol moves out of
  `implement.md` (which now delegates, as `orchestrate` already did) into a skill, and gains the
  part that was missing. The rule is stated once — **a worktree touches nothing outside itself
  except by explicit allowance** — and backed by a **10-class enumeration** of what a worktree
  can still reach (databases, migration history, ports, containers/compose, credential stores &
  secret env, external caches, sequence-numbered artifacts, external tenancies, machine-global
  files/sockets, the shared `.git`), each with a disposition: **isolate** / **forbid** /
  **accept**. Deliberately *not* two patches for the two failures we tripped over (a shared
  `byline_test` dropped mid-run; a migration applied to shared dev from a since-discarded
  branch) — both were the same shape, *two checkouts, one name, one object*, so the class is
  what gets fixed. A **preflight** runs before any ≥2 batch and states each present class's
  disposition; **unclassified is not a pass** — it means sequential dispatch, not a gamble.
  Includes the isolation-key convention (worktree-derived, never random — cleanup depends on
  it), a symptom→class fault table, and the linked-worktree test
  (`git rev-parse --git-dir != --git-common-dir`).
- ☑ **Env carry-in + the environment-fault class** (the expensive finding). A worktree holds
  the tracked tree at HEAD and nothing else, so every gitignored env file is **absent** and
  secret-backed variables resolve to *empty* rather than erroring — the failure then surfaces
  deep in app code. In the pilot two capable agents independently reported four frontend test
  failures and both concluded "pre-existing code breakage"; the tests were green on the
  integrated branch. That is worse than a wasted cycle: it is a confident wrong diagnosis that
  can lead an agent to "fix" working code. Two halves: **prevention** — the skill's carry-in
  step copies the gitignored env files into each worktree and *verifies* resolution against the
  main tree, where a variable resolving in one and not the other is a hard stop; and
  **diagnosis** — `systematic-debugging` gains an **Environment faults** section making the
  verdict "pre-existing breakage" require two checks first (does it reproduce on the main tree;
  did the config resolve). Reported as `ENV-FAULT:`, owned by nobody, never fixed in code,
  never consuming a QE fix round. Wired into both dev agents + devops (worktree blast radius),
  `quality-engineer` (env faults listed separately from defects), implement's triage, and
  `observability` (`env_faults`, additive — schema id unchanged).
- ☑ **File overlap is a DAG edge.** The pilot batched T8 with T10/T12 correctly per the declared
  graph and they still collided: no dependency edge, same repository file. `deps:` records what
  must exist before what; it does not record what cannot happen *at the same time*. So
  **effective graph = declared `deps:` ∪ `touch:` overlap**, computed before batching, with the
  added edges reported like drift. `touch:` becomes **binding** rather than commentary
  (spec-driven skill): repo-relative paths or globs, `unknown` written explicitly rather than
  omitted or guessed. **Glob overlap counts** — which is what handles the migration case that
  was worked around by hand in the pilot: two tasks creating in `db/migrations/*` collide on the
  *counter*, and their merge is clean while the ordering is wrong. `/wellforge:tasks` gains an
  overlap check at derivation time (declare the edge, merge the tasks, or say why). Phase 13's
  merge-conflict detection stays as the backstop for overlap the lists failed to declare.
- ☑ **ADRs must state the failure shape** (the meta-finding). ADR 0013 in the pilot described
  its rule at *mechanism* level; an agent who had read it, and was actively applying it on the
  read side, reintroduced the same defect on the write side. Correct rule, correctly followed,
  and it still didn't transfer. `adr-writer`'s MADR template gains a required **`## Failure
  shape`** section — the class of mistake, stated so it's recognisable in a context we haven't
  met — plus a **symmetry test** (read/write, request/response, serialize/deserialize: would
  this text catch me in the mirror-image position?) and "no failure shape" as a legitimate,
  explicit answer for pure preferences. The `AGENTS.md` one-liner — often the only part a
  future session reads — now leads with the shape, not the ban.

Deferred to its own cut (template series, so a `vX.Y.Z` release per `docs/VERSIONING.md`):
**per-worktree test-database naming** and a **dev-database guard** in the presets. The plugin
can refuse to *dispatch* into an unsafe batch, but a guard that refuses to run at all from a
linked worktree belongs to the project's own task definitions — the only layer that also covers
a human running the command by hand. That cut is also the right moment to answer the question
this phase deliberately left open: **is the dev database reachable from a worktree at all?**
The skill forbids it by default until a project says otherwise.

**Follow-up fix** (plugin `2.27.6`, 2026-09-20): the integration recipe did not run. Step 3
said `git rebase <feature-branch> <worktree-branch>` from the main tree, and git refuses that
outright — `fatal: '<branch>' is already used by worktree at '<path>'`, exit 128 — because the
branch is checked out in the worktree. Reproduced in a scratch repo, then fixed and re-run
end to end on a two-track batch: the rebase belongs **inside** the worktree
(`git -C <worktree-path> rebase <feature-branch>`), after which `merge --ff-only` from the
main tree works fine while the worktree still exists. Consequence: integration needs the
worktree **path**, not just its branch, so step 2 now asks the agent for `WORKTREE-PATH:` and
step 3 carries a `git worktree list --porcelain` derivation as the fallback. The same section
also contradicted itself — "never a merge commit" three lines above a parenthetical blessing a
`--no-edit` merge-back — so that is replaced by what a refusal actually means: `fatal: Not
possible to fast-forward` says the branch was not rebased onto the current tip, and the answer
is to rebase again, never a flag that forces the merge through. The strongest evidence yet for
this phase's own honest status below: a recipe nobody had executed.

Honest status: prompt-authored, not yet exercised through a real parallel batch — same caveat
Phase 13 carried, and the reason this phase exists. Validation is the next pilot batch, which is
also the only thing that can tell us whether the preflight's sequential fallback fires too often
to be tolerable.

## Phase 17 — Reflexive pass: self-critique before the verifier (added 2026-09-20)

Goal: close the one AI-agent design pattern WellForge had no answer for. Mapped against the
five standard patterns, the plugin covers single-shot (`status`, `triage`), iterative ReAct
(`spike`, dev agents' verify loop), planner-executor (`orchestrate` — the core design) and
verifier-gated (QE deterministic + evaluator adversarial, doubled). **Reflexive** —
generate → self-critique → refine — existed only inside `frontend-design` Pass 2. Everywhere
else an artifact went straight from its author to an expensive reviewer, so a vague AC or a
test that asserts a mock cost a full human-gate, QE or eval round to discover.

- ☑ **`self-critique` skill** (plugin `2.27.0`) — the authority; agents and commands delegate.
  Three rules: **one pass, never a loop** (unbounded self-refinement drifts toward the
  author's taste and burns tokens), **against a checklist, not vibes** ("looks good" on every
  item means the pass didn't happen), and **never self-approve**. Five per-artifact checklists
  of failure modes observed to survive an author's own read — spec.md (unverifiable AC, hidden
  AND, solutioning in the WHAT, assumption smuggled in as fact), plan.md (AC→test gap, prose
  contract, idealized codebase, reflex `Security: NO`), design.md (missing loading/empty/error
  state, unjustified NEW), tasks.md (`done when:` nobody can run, a `touch:` list that lies —
  a scheduling edge, so an omission is a pre-scheduled collision), and code (a test that cannot
  fail, shape drift from plan.md, a corner cut to make something pass).
- ☑ **Wired** into product-owner, architect, designer, frontend-dev, backend-dev and devops
  (one section + a one-line result in each agent's return), and into the main-loop commands
  that write artifacts themselves — `/wellforge:spec` (new step 4), `/wellforge:plan` (step 5),
  `/wellforge:tasks` (step 6); `/wellforge:design` relays the designer's line. `orchestrate`
  and `implement` relay the line so a human gate sees what was already caught. Tier-gated in
  `rigor-tiers`: **off at `spike`** (no agents, and `// SPIKE:` already records the cut), on at
  `mvp`/`production`.
- ☑ **Anti-gaming**, the part that makes this safe to add: the evaluator is explicitly
  forbidden from crediting an author's own review — a "Self-critique: clean" line is a claim
  about an artifact, not evidence about it. The pass gates nothing and blocks nothing;
  independent verification stays the authority. Copilot gets the rule repo-wide in
  `copilot-instructions.md` (it runs one chat mode at a time, so the human *is* the next
  reviewer there); OpenCode picks the skill up through the generic skill copy.

Honest status: prompt-authored, verified by re-running both adapter generators and the
model-routing guard. No runtime teeth and deliberately none — a hook cannot tell a real
critique pass from a line of text claiming one, which is precisely why the evaluator is told
to ignore the claim. What would falsify the phase: human-gate iterate-rounds per spec, and
QE/eval first-round FAIL rates, before vs. after. Both need the Phase 7 pilot.

**Follow-up fix** (plugin `2.30.0`, 2026-09-20): three gaps where a command's inputs didn't
match its outputs. `/wellforge:status`'s phase table needed "QE passed" to route an `mvp`
feature, but its Gather step never collected a QE verdict — QE writes no artifact, so the
verdict exists only in `.forge/runs/`, which `/wellforge:triage` reads correctly and status
did not. Status now reads it the same way, and the table distinguishes PASS / FAIL /
**unknown** rather than treating a missing verdict as a pass. `superseded` was defined in the
spec-driven lifecycle diagram and implemented nowhere: no command set it, none read it, so an
abandoned spec stayed `in-progress` forever and `/wellforge:triage` reported it as rot with no
way to clear it. It now belongs to `/wellforge:done --superseded-by <NNN-slug>` — the same
guarded place every other status transition lives, with no done gate (nothing was claimed, so
there is nothing to verify), a refusal on an already-`done` feature, and a required successor
that must resolve. `status` shows it as retired, `triage` skips it but flags a dangling
`superseded_by:` as a broken pointer. Third, `triage` wrote `command: triage` into run traces
while the observability schema's enum listed five values not including it — the enum now has
six. Small, but it is the schema half of a trace that an evaluator reads as trajectory
evidence.

**Follow-up fix** (plugin `2.31.0`, 2026-09-20): the packaging and prose layer. The plugin
README listed **13 of 19 commands and 7 of 18 skills** and omitted the `context-hub` MCP
server — a command nobody can find is a command that does not exist — and `plugin.json` had
drifted a patch ahead of the version CLAUDE.md quoted. Both are now enforced by
`scripts/check-docs.py` (README covers every command/skill/MCP server, version in sync,
every skill description within the loader's 1024-char limit, no dangling `[[wiki-link]]`),
wired into ci.yml beside the routing guard. `notify.sh` had two injection surfaces: the
message text was interpolated into an AppleScript string (a `"` ends it and the rest runs)
and sent to Telegram with `parse_mode=Markdown` and no escaping, so an unpaired `_` or `*`
— `snake_case_name` — returned a 400 the user never saw, because the call is backgrounded
with output discarded; now argv-passed and plain-text, with `--data-urlencode` (`-d` does
not encode, so an `&` truncated the field). `pre-compact-backup.sh` and `session-start.sh`
ran in **every** repo where the plugin is enabled at user scope, the former writing
`.claude/transcripts/` into unrelated projects; both now carry the same
`specs/`-or-`.forge/` scope test `trace-subagent.sh` always had. Roadmap leakage
(`Phase 7 pilot`, `US-3 / AC-3.1`, a `docs/plans/PLAN.md` pointer) is gone from shipped skill and
command prose — those identifiers resolve to nothing in a user's project. And the tier/terse
Step 0 and the QE-FAIL triage table, duplicated verbatim across implement / orchestrate /
promote, are now defined once in `rigor-tiers` with each command citing it and stating only
its own deviation.

## Phase 18 — Operability: doctor, dry runs, the third exit, portable conventions (added 2026-09-20)

Not defects — five gaps where the plugin promised or implied something it didn't carry.

- ☑ **`/wellforge:doctor`** — health check with a fix command per FAIL: toolchain
  (`jq` in particular, whose absence makes every hook exit 0 while doing nothing), declared
  MCP servers, hooks whose scripts exist and are executable (a missing one fails *open*),
  both drift guards, project shape and template-drift, and the git policy config. `--tests`
  runs the four regression matrices from the installed plugin, which is otherwise only
  possible by pushing. It closes with the command index, so it doubles as the `help` the
  plugin never had. Read-only by hard rule: it diagnoses, it never fixes.
- ☑ **`--dry-run` on `upgrade`, `promote`, `adopt`** — previously only `release` had one,
  and these are the three commands that rewrite a repo that already exists. Same shape each
  time: what would change, what would run, what is irreversible, and **what it cannot
  predict** (upgrade's `--pretend` doesn't resolve conflicts; promote can't know whether the
  eval will pass; adopt's plan is only as good as its survey). A dry run spawns no agents —
  an agent that runs has already changed the world.
- ☑ **`archived` — the third terminal status.** `/wellforge:status` and `/wellforge:triage`
  had been telling users to "promote or archive" since they shipped, with no archive to
  reach for: the only exits were to finish the work, lie with `done`, or hand-edit
  frontmatter. Now `/wellforge:done --archive "<reason>"`, reason **required**, alongside
  `--superseded-by`. Distinct from superseded (another spec took over) and from done (it
  shipped); triage skips all three.
- ☑ **Three skills for conventions the plugin kept citing but didn't carry** —
  `git-policy` (the commit format, the rebase-not-merge rule, the four enforcement layers,
  and what to do when a gate rejects you), `quality-gates` (the catalogue, the
  referenced-never-copied calling convention, tier behaviour, and how a threshold changes),
  and `template-contract` (one root copier.yml, the shared questions, the manifest, the two
  version series). All three existed only as repo files — `CLAUDE.md`, `gates/README.md`,
  `templates/_shared/CONTRACT.md` — which a *generated* project cannot read. An agent
  working in a scaffolded project now carries them.

`check-docs.py`, added hours earlier, caught the new command and all three skills missing
from the README before this was committed. That is the intended failure mode.

**Follow-up to the stop-verify fix** (plugin `2.34.1`, 2026-09-20): making the drift check
branch-wide gave it a surprising failure mode — a one-line typo fix in `spec.md`, committed
several commits back, blocks *every* Stop for the rest of the branch. That is the rule
working, but "I fixed a typo and now Claude can't stop" doesn't feel like a rule working.
Worse, testing it showed **the prescribed escape did not work**: `/wellforge:tasks` re-sync
on a cosmetic edit correctly changes nothing, `tasks.md` stays out of the change set, and
the hook keeps blocking while telling the user to run the command they just ran. Fixed by
making re-sync **always stamp `synced: <date>`** — which is also the honest record (the task
list was re-checked against the spec; it did not have to change) — and by rewriting the hint
to name the fix, the branch-wide scope, and why an old commit is implicated. Documented in
the drift rule and the hook table; two regression cases pin both halves.

**Follow-up — the one hole in defer-don't-lower** (plugin `2.35.0`, 2026-09-20): tier
precedence put `--mode` above a feature's recorded `rigor:` unconditionally and silently, so
a `production` feature could be run at `mvp` for a pass — skipping architect, designer and
the eval — with nothing said. The flag still wins (there are honest uses: two quick tasks
before the full pipeline), so the rule is enforced by **announcement**, not refusal: a
downgrade now prints what it skips, that the recorded tier is unchanged, and that
`/wellforge:done` still gates at the higher tier — which was already true and is the reason
allowing it is defensible. A raise needs no warning. It is also recorded (`rigor_recorded`
in the run trace) and **surfaced** by `run-report.py`, so a cheap run stays legible after
the transcript scrolls away; recording without surfacing would have been archival, not
useful. Defined once in `rigor-tiers`, so implement and orchestrate inherit it.

**Cosmetic cleanup that wasn't** (plugin `2.35.1`, 2026-09-20): converting 52 inert
`[[wiki-links]]` into relative markdown links that actually resolve required checking they
survive the adapters — which is how the **adapter generators were found emitting all 44
skill files EMPTY**, in both OpenCode and Copilot, for as long as that code has existed.
Cause: `open(p, "w").write(translate(open(p).read()))` — Python evaluates `open(p, "w")`
before the argument, truncating the file to zero, so the read returns `""`. The generators
reported "44 skill files" throughout, because they counted files, not bytes. Fixed in both,
with an `assert_nonempty()` that refuses to finish a generation containing a zero-byte file.
The skill library those two tools ship has never actually contained anything until now.
Pricing was also re-verified against the **live** page rather than the `claude-api` skill's
cached table (a cache checking a cache): every base rate matched, six older/retired models
were added so an old id in a trace is not priced at a fifth of its cost, and the
not-modelled multipliers are now named with their sizes.

## Phase 29 — The CLI gets its own release series (added 2026-09-20)

`Formula/wellforge.rb` pinned the **template** tag, so the CLI could only ship when the
template shipped — and the release rules require a template release to carry a template
change. The result was not a slow channel, it was no channel: `scripts/wellforge` sat
**179 insertions / 64 deletions** past `v0.9.0` with nothing to ride on, while
`wellforge doctor` called every brew user's checkout current.

- ☑ **`cli-vX.Y.Z`, the fourth series** in `docs/VERSIONING.md`, with the same rules as the
  other three and one extra: semver by *user-visible CLI behaviour*, where major means a
  removed subcommand, a renamed flag or a changed exit-status contract — scripts depend on
  those.
- ☑ **`WELLFORGE_CLI_VERSION` is the single source.** `wellforge version` prints it, the
  Formula's `test` block asserts it, CI asserts it equals the newest `cli-v*` tag. The
  Cellar-path derivation that used to *be* the version is kept only as a cross-check.
- ☑ **`check_cli`** — the brew CLI and the checkout's copy are two different files, and
  `wellforge update` pulls the checkout *before* upgrading brew, so the fix you just pulled
  is not the one running. Doctor names both versions; `update` reports the constant it
  moved from and to, read out of the file brew installed (the running process is still the
  old CLI and cannot report the new version by looking at itself).
- ☑ **`scripts/release-cli.sh`**, plan-only by default, with a `--formula-only` recovery
  mode.

**Why a CLI release is two commits, measured rather than assumed.** The Formula pins the
sha256 of GitHub's generated tarball, which does not exist until the tag is pushed — and is
not reproducible locally. For the existing `v0.9.0` tag: GitHub `b61eafcb…` (what the
formula pins) vs a local `git archive` of the same tree, `746cc34f…`. So the tag comes
first and the sha second, always.

**Starting at 1.0.0, not 0.1.0**, because the formula already resolved `0.9.0` from the
template tag: a lower number makes `brew upgrade` a silent no-op for everyone who already
installed it. `version` is now explicit in the formula rather than parsed from the url.

**Found while verifying:** `brew audit --strict` rejects `license "UNLICENSED"` as a
non-standard SPDX identifier (now `:cannot_represent`). That finding also **corrected last
phase's claim** that audit can only run after publication — it refuses a *path*, but runs
in ~1.4s against a tapped repo, which is how the finding surfaced.

**Left undone, and it needs a push:** the Formula still names the `v0.9.0` tarball. It can
only move once `cli-v1.0.0` is pushed and its sha can be fetched —
`scripts/release-cli.sh 1.0.0 --formula-only --execute` finishes it. The suite carries that
as an xfail so the gap is visible rather than assumed away.

## Phase 28 — The CLI gets a regression matrix, and CI gets both halves (added 2026-09-20)

`scripts/wellforge` is the first thing a teammate runs and was the only untested code in
this repo — the hook matrices, run-report, forge-state and the adapters all had a suite. CI
never touched `scripts/` or `Formula/` at all.

- ☑ **`scripts/tests/wellforge.test.sh`** — 17 cases, same contract as the hook matrices:
  drives the REAL script against a temp `HOME`, a temp `PATH` of recording shims
  (brew/claude/gh/docker/mise/uvx/npm/curl/open) and **real git fixtures with a real bare
  upstream**, because "N commits behind" is worth measuring rather than mocking. Shims log
  their calls, which is the only way to assert a behaviour that produces no output — "update
  must not reinstall a plugin that is already current".
- ☑ **An `xfail` marker with teeth.** Four cases describe behaviour later work introduces;
  they do not fail the suite, but an **XPASS does** — a marker that has quietly become true
  is a lying test. Each was verified to fail for its stated reason, not incidentally.
- ☑ **A watchdog per case.** Not a nicety: `wellforge telegram` with an exhausted stdin
  spins forever (read fails → empty token → `continue`). Without the watchdog one such
  regression hangs CI to the job limit instead of failing in seconds. `timeout(1)` is absent
  on a bare macOS, so it polls a background job.
- ☑ **`cli` job in ci.yml** — `shellcheck -s bash --severity=warning` over
  `scripts/wellforge`, `scripts/*.sh` and the plugin's hook scripts, then the matrix.
- ☑ **Mutation-tested, twice.** Flipping `set -uo` back to `set -euo` reddens 2 cases;
  additionally restoring the original `grep | sed` version read reproduces the Phase-27
  defect exactly — `expected rc=1, got rc=2`, missing collisions/telegram/summary. A suite
  that cannot reproduce the bug it was written for is decoration.

**Found by the new checks, on their first run:** a dead `TOTAL=0` in `fleet-cost.sh`
(SC2034), and `FormulaAudit/Desc` in `Formula/wellforge.rb` (a description starting with the
formula name). Both fixed. Also found while building the suite: the telegram wizard's
infinite spin above, now pinned as an xfail.

**`brew audit` stays a manual pre-release step, with evidence.** It refuses a path outright
("Calling `brew audit [path ...]` is disabled"), so it can only run against the published
tap — which does not exist until after the release. A CI job could run at most half the
check, on a `macos-latest` runner billed at 10×, for a file that changes once per release.
`brew style` (1.5s, path-based) is in `docs/VERSIONING.md` as the pre-tag step instead.

**Known gap, stated in `scripts/README.md`:** the suite runs on `ubuntu-latest` while the
CLI targets macOS, so BSD-vs-GNU differences are not covered by CI.

## Phase 27 — The deferred half: per-worktree databases (added 2026-09-20)

Phase 16 shipped the parallel-execution discipline and deferred its template half. Until now
the `worktree-isolation` skill said databases were class-1 shared state, the preflight had no
way to isolate them, and the honest consequence was that **most backend batches of ≥2 ran
sequentially**. This is that half, in `templates/spring-kotlin-react` and
`templates/hono-react` — template `v0.10.0`, its own tag, no plugin coupling.

- ☑ **One derived identity** — `.wellforge/worktree-id.sh` turns
  `sha256(git rev-parse --show-toplevel)` into `suffix` / `id` / `port` / `linked`. POSIX sh,
  verified under `dash`. Injected through mise `[env]`, which supports Tera templating and
  `exec()` — so **two** subprocess calls produce `WF_DB_NAME`, `WF_DB_PORT` and
  `COMPOSE_PROJECT_NAME`, and nothing is hard-coded anywhere.
- ☑ **The primary tree keeps the plain name and port 5432.** Deliberate: adopting this must
  not orphan a dev database someone has data in. Only linked worktrees are suffixed.
- ☑ **Tests use Testcontainers, dev uses a per-checkout compose project** — and both presets'
  DEFAULT `test` lane stays Docker-free (`test:integration` is its own lane, failsafe `*IT`
  on the JVM, a second vitest config on Hono). Requiring Docker for unit tests would have
  been a real regression traded for a theoretical one.
- ☑ **`mise run db:guard`**, shipped by the template, not the plugin — the skill's own
  "where the guard lives" rule. Wired into `dev`, `test` and every migration task.
- ☑ **The skill's class-1 row is now version-aware**: `v0.10.0`+ reads as isolated, older
  projects keep the sequential rule, and the preflight reads `.forge/manifest.json` to
  decide. Its isolation-key example — `basename` — was replaced: a basename collides across
  repos, is not a legal database identifier, and yields no port offset.
- ☑ **CI asserts the property, not the plumbing** (`worktree-isolation` job, both presets):
  three checkouts derive three identities, the guard refuses a foreign database, two
  worktrees bring their databases up concurrently, and A cannot reach B's. Toolchain-free
  (`mise env` needs no Java or Node), so it costs seconds.

**Measured end to end**, both presets, two worktrees each, concurrently:

| | hono-react | spring-kotlin-react |
|---|---|---|
| integration lane | 2/2 tests × 2 worktrees, throwaway DBs on ports 32772 / 32773 | 2/2 tests × 2 worktrees, containers on 32782 / 32783 |
| dev compose | `my_service_wt5470c47c`:5908 vs `my_service_wt429aa1c0`:5640 | `my-service_wt25135e0b`:5683 vs `my-service_wt76d29864`:5492 |
| cross-reach | `database "…" does not exist` | `database "…" does not exist` |

**Two pre-existing blockers had to be fixed to verify any of it**, both of the
never-executed species this plan already names: `spring-modulith-starter-jooq` has never
existed in any published Modulith release (the POM would not parse, so the JVM preset could
not build at all), and Testcontainers 1.20.4 cannot find Docker under OrbStack. Fixed as
their own commit.

**Still open, reported not fixed:** the spring preset's own Kotlin fails its own ktlint gate
— 20 violations across 4 files that predate this work (`DomainError.kt`, `Result.kt`,
`GlobalExceptionHandler.kt`, `ModularityTest.kt`), so `mise run lint` is red in a fresh
scaffold. Out of scope here; `mise run backend:lint:fix` is the one-command fix, and CI does
not catch it because no job lints a generated project.

## Phase 26 — A real distribution path, and adapters that cannot ship broken (added 2026-09-20)

Two problems with the same shape: something that *looked* shipped and was installable or
readable by nobody. `.claude-plugin/marketplace.json` read `"source": "./wellforge-plugin"`
— an install that works on exactly one machine, the one holding the clone. And both adapter
generators printed a healthy file **count** whether or not the files had content, links that
resolved, or model names that matched the routing policy.

- ☑ **The marketplace installs from git** — `git-subdir` source (`url` + `path` +
  `ref`), pinned to a `plugin-vX.Y.Z` tag. Format verified against the current plugin-
  marketplace docs rather than recalled; the observed shapes in
  `~/.claude/plugins/known_marketplaces.json` corroborate it.
- ☑ **The plugin became the third tag series.** A `ref` has to name something immutable, so
  `plugin-vX.Y.Z` joins `vX.Y.Z` and `gates-vN` in `docs/VERSIONING.md` — with the
  never-tag-two-series-on-one-commit rule restated for three, and the `plugin-v` prefix
  keeping it PEP440-unparseable so copier never offers the plugin as a template upgrade.
- ☑ **One release, four places, one guard.** `check-docs.py` now fails when `plugin.json`,
  `marketplace.json`'s `version`, its `source.ref` and CLAUDE.md disagree. It caught its own
  introduction (manifest at 2.42.0, plugin.json still 2.41.0).
- ☑ **`/wellforge:release` grew a WellForge branch.** It previously disclaimed the plugin
  release outright, which left the procedure nowhere. Step 0 now routes by repo.
- ☑ **Generated projects declare their plugin** — `extraKnownMarketplaces` +
  `enabledPlugins` in `.claude/settings.json`, and `plugin.marketplace` in the manifest
  (`wellforge@wellforge` vs `local`: provenance a teammate can or cannot reproduce).
- ☑ **`/wellforge:doctor` reports the install source** — marketplace vs local-directory
  marketplace vs `--plugin-dir`, and whether a newer `plugin-v*` tag exists.
- ☑ **`adapters/smoke-test.py` + a CI matrix job** — generates each adapter and asserts
  (a) no empty file, (b) every relative link resolves, (c) every command/agent/skill has a
  counterpart or is declared absent in a machine-read block in the adapter README,
  (d) generated model names match `config/model-tiers.yml` (via `check-routing.py`, which
  gained `--glob`/`--name-re` so it can read namespaced generated filenames).
- ☑ **It found real defects on its first run**: two Copilot links that resolved in the
  plugin tree and pointed at nothing in the generated one (fixed with a `relink()` pass —
  the breakage was *relocation*, not a bad source link), a README status line that had
  drifted to 17 prompts / 13 skills / 3 MCP servers against an actual 20 / 21 / 4, and two
  stray `</content>` lines left in committed markdown.
- ☑ **Each assertion was mutation-tested** before being trusted: truncate a file, inject a
  broken link, delete a counterpart, stale the declared-absent list, corrupt a model name —
  all five caught, on both adapters. Four green checks that never go red are worse than no
  checks.

**Undocumented, so not claimed.** What `claude plugin update` resolves to — the refreshed
manifest's `ref`, the default branch, or the `version` field — is not specified in the
published docs. `VERSIONING.md`, the plugin README and `doctor.md` all say so and point at
the one observable fact: the version recorded in `installed_plugins.json` afterwards. The
same applies to project-scope `enabledPlugins` — it declares, and no claim is made that it
installs.

## Phase 25 — Make the cost numbers actionable (added 2026-09-20)

`.forge/runs/` carried tokens and an estimated cost, and `model-routing.yml` said to move
agents down a tier "only with evidence". No command consumed either. A number nobody reads
is a number nobody maintains.

- ☑ **`config/rigor-budgets.yml`** — per-tier soft ceilings (feature / run / wall-clock per
  batch) and the rework thresholds, `advisory_only: true`.
- ☑ **`run-report.py --budget`** (spend vs ceiling, %, top consumer by output tokens) and
  **`--rework`** (fail rounds per feature and per agent, plus repeat dispatches inside one
  run). 18 new test cases.
- ☑ **Three states, not two.** `unknown` — no token events captured — is never reported as
  `within`. Every trace in this repo prices at $0.0000 because `.events.jsonl` was never
  written for them, so a two-state check would have reported the whole fleet as comfortably
  under budget while measuring nothing.
- ☑ **triage gains signals 6 and 7** (over budget, rework hotspots), each with the
  deterministic query that produced it, and each told to report `unknown` in a footer
  rather than as a finding. Rework is surfaced as a **question**: the count does not say
  whether the agent was too cheap, the spec was wrong, or the work was hard.
- ☑ **`scripts/fleet-cost.sh`** — org sweep: features in flight, rework rounds, top rework
  agent per repo. It deliberately does **not** recompute cost: the pricing table lives with
  the plugin, and a fleet sweep guessing at prices is worse than one that says where to look.
- ☑ **`model-routing.yml` now names its own evidence standard** — the rework metric, both
  directions, with what it does *not* say (whose fault the rework was).

Honest limit, stated in three places: the cost estimate undercounts structurally, so these
are relative tripwires for spotting outliers, not dollars.

## Phase 24 — Dispatch the specialists from data, not memory (added 2026-09-20)

The security floor is called non-negotiable, and the specialist that reviews the code behind
it ran when someone thought of it. Same for ADRs: the architect listed candidates and
whether one became a record depended on the orchestrator remembering to ask.

- ☑ **`config/security-triggers.yml`** + **`scripts/security-triggers.py`** — path globs
  and sensitive-surface substrings, evaluated against the **union** of the batch's declared
  `touch:` globs and the real `git diff --name-only`. Intent and reality both count: `touch:`
  catches the surface before the code exists, the diff catches the file nobody declared.
  `always_at_tier: [production]`.
- ☑ **`/wellforge:implement` Step 3b and `/wellforge:orchestrate` step 9** run it after
  integration, before QE. Findings ≥ medium route through the same owner table and 2-round
  cap as QE failures, so the two loops cannot drift apart. Missing script → dispatch anyway:
  one extra mid-tier agent beats an unreviewed auth change.
- ☑ **`verdicts.security`** joins qe and eval in the trace (schema **v3**; v1 and v2 still
  read). Absent ≠ PASS — at `production` every batch is reviewed, so a missing verdict means
  the review never ran, and `forge-state.py` makes that a failing done-gate condition.
  `/wellforge:done` inherits it automatically, since it reads that gate.
- ☑ **ADRs dispatch from the plan's own text**: a decision that names a rejected alternative
  is an ADR by definition. Automatic at `production`, offered at `mvp`, path predictable
  (`docs/adr/NNNN-slug.md`) and cross-referenced from the plan. A decision with no rejected
  alternative is explicitly *not* an ADR — writing one for it trains people to skim ADRs.
- ☑ **51-case glob matrix**, which caught the trap it was written for: a naive `**/`
  pattern misses top-level `migrations/001.sql`.

Cost: one extra mid-tier agent per matched batch, and every production batch matches.

## Phase 23 — Which plugin set this project up (added 2026-09-20)

`.forge/manifest.json` recorded the **template** version, which is what makes `copier
update` work. It recorded nothing about the **plugin** — yet the project's `AGENTS.md`
conventions, the spec-driven file formats, the `.forge/runs/` trace schema and the hooks all
move with it. A project scaffolded by 2.20 and driven by 2.39 was invisible.

- ☑ **A `plugin` object** — `{version, set_by: new|adopt|upgrade, at}` — in
  `.forge/manifest.json`, and the same in `.forge/adoption.json` (which previously held
  `plugin` as a bare string; readers accept both, writers emit the object).
- ☑ **Written by the command, never a copier answer**, documented in CONTRACT.md with the
  reason: a persisted answer replays the scaffold-time version forever, because `copier
  update` re-renders from recorded answers — the field would be wrong at exactly the moment
  it matters. The general rule it follows: *a value that depends on when the command ran is
  written after generation; only what the user answered is a question.*
- ☑ **`docs/PLUGIN-MIGRATIONS.md`** — project-side changes per plugin minor, with the test
  for what belongs there (*would a project set up by the older plugin be wrong, incomplete
  or noisy under the newer one?*). `/wellforge:upgrade` applies or surfaces every entry
  between recorded and running, as a first-class step beside the template re-render, and
  stamps the manifest at the end — including on a plugin-only upgrade, which is exactly the
  case that would otherwise leave a stale value.
- ☑ **`/wellforge:doctor` reports four states**, and the one that matters most is the
  common one: **absent** is a WARN with the fix, not an error, because it is the normal
  state of every project older than this field. Newer-project-than-plugin is the FAIL.
- ☑ **Trace schema `wellforge-run/v2`** adds `plugin_version`; `run-report.py` accepts v1
  and v2, and both test suites assert that a v1 trace still loads and still yields its
  verdict. A schema bump that orphans the history it exists to preserve is a bad trade.
- ☑ `fleet-status.sh` gains a plugin column, reported alongside template staleness rather
  than folded into it — a project can be current on one and behind on the other.

Honest gap: the claim that a command-written `plugin` key survives `copier update` is
reasoning, not a measurement — three attempts to exercise a real update were refused by
copier before the merge (local template source). It is not load-bearing, since upgrade
rewrites the object, but it is unproven.

## Phase 22 — What the plugin costs before you type (added 2026-09-20)

Nobody had measured the toll. Claude Code injects every skill, command and agent
**description** into every session prompt in every project where the plugin is enabled —
bodies are lazy, descriptions are not — so 51 items are paid for in repos that will never
run a WellForge command.

- ☑ **`scripts/check-budget.py`** + **`config/budget.yml`**: per-item table sorted by size,
  totals by kind, estimated tokens at chars/4 (**stated**, since the true count is
  tokenizer-specific), a hard per-item 1024 limit, and a total ceiling enforced in CI.
  Measuring it found its own bug first: strict YAML parsing skipped 14 of 20 commands
  (`argument-hint: [x]` is a valid Claude Code hint and an invalid YAML flow sequence), so
  the first number was a third too low.
- ☑ **Compressed the ten largest** under the terse-compress fact-preservation gate, run
  mechanically: every trigger phrase and "do NOT use" clause asserted present in the
  compressed text or the file left untouched. **20,351 → 19,540 chars** (~5,088 → ~4,885
  est. tokens); −11% across the ten.
- ☑ **The −30% target was not reachable, and that is the finding.** What remains in these
  descriptions is trigger phrases and disambiguation clauses — the routing logic itself.
  The gate refuses to drop them, correctly. So the ceiling is a **ratchet at today's exact
  total** rather than the 85% asked for: you cannot add a character without removing one, or
  moving the number in its own commit. The arithmetic to reach 85% is written in
  `budget.yml`, and it runs through the stack skills.
- ☑ **ADR 0001** (first in this repo): the five stack skills **keep** full descriptions.
  They are 3,288 chars (17% of the total) and almost entirely trigger phrases; the token
  cost is measurable and certain, the mis-routing cost of shortening is real and — with no
  skill-trigger eval suite in this repo — unmeasurable. Optimising the measured side against
  the unmeasured one is the failure the ADR names. Revisit when either changes; shipping the
  stack skills as a separate optional plugin is the first alternative if the budget bites.

## Phase 21 — The lifecycle rules as mechanism (added 2026-09-20)

Two rules the commands were rewritten around — **only `/wellforge:done` writes
`status: done`**, and **`rigor:` only ever rises** — were enforced by nothing. Any `Edit` to
a spec's frontmatter flipped either field, and "the single guarded place" stops being single
the first time anyone takes the shortcut. `stop-verify.sh` had already shown the move for the
drift rule; this is the same for the other two.

- ☑ **`hooks/scripts/post-spec-guard.sh`** (PostToolUse on Write/Edit/MultiEdit, scoped to
  `specs/*/spec.md|brief.md` inside a WellForge project). Diffs the frontmatter against
  `git show HEAD:<path>` and refuses: `status: done` unless `forge-state.py` reports
  `done_gate.passes` for the resolved tier (the `failing` list quoted verbatim), any downward
  `rigor:` move, reopening a closed feature by edit (`superseded`/`archived` excepted), and
  any status or tier outside the enum.
- ☑ **Honest about what it is.** PostToolUse runs *after* the write, so it cannot prevent the
  edit — it blocks the turn and names the revert. A PreToolUse version would have to parse
  proposed content out of three different tool shapes and reason about a patch it cannot
  apply: more ways to be wrong, on a rule whose violation is cheap to undo.
- ☑ **Two carve-outs, both deliberate.** A `spike` closes on prose in `brief.md`, so
  `done_gate.passes` is `null` and the hook allows it, saying so. And a spec that is *created*
  already `done` is a record of prior work (the brownfield adopt shape), not a transition —
  allowed, loudly, because no gate about tasks and QE runs can be satisfied by work that
  predates the spec.
- ☑ **Fails open, deliberately.** No `jq`, no `pyyaml`-capable python and no `uv`, or
  `forge-state.py` missing → advisory warning, exit 0. A guard that blocks when it cannot
  evaluate is a guard people switch off. (It resolves `uv run --with pyyaml` when the system
  python lacks yaml, which is most machines — otherwise the guard would fall open almost
  everywhere.)
- ☑ `hooks/scripts/tests/post-spec-guard.test.sh`, 18 cases, wired into ci.yml.

## Phase 20 — Deterministic feature state (added 2026-09-20)

`/wellforge:status`, `:triage`, `:done` and `:promote` each had the model read every spec's
frontmatter, count `tasks.md` checkboxes and call `run-report.py` for verdicts — **four
re-derivations of one state**, on every heartbeat. Slow, priced as judgment though it is
discovery, untestable, and unable to reject `status: doen` (which a model reads as
approximately-`done`). The heartbeat skill already drew the line; this phase implements it.

- ☑ **`config/spec-frontmatter.schema.json`** — machine-readable mirror of the spec-driven
  skill's frontmatter for spec/brief/plan/design/tasks/eval-report, including the three
  conditionals the lifecycle implies (`superseded` needs `superseded_by`, `archived` needs
  `archive_reason`, `done` needs `done:`). The **skill stays the authority**; `check-docs.py`
  fails if the status/rigor enums drift between them, so neither can be edited alone.
- ☑ **`scripts/forge-state.py`** → the `forge-state/v1` envelope: per feature the status,
  kind, tier (+ where it came from), artifacts, task counts, drift, QE/eval verdicts joined
  from `.forge/runs/`, the tier's `done_gate {passes, failing}`, and `problems[]`. Run-trace
  loading is imported from `run-report.py`, not duplicated. Drift uses **commit order**, not
  commit dates — dates are second-granular, so two commits in the same second tie, and a tie
  reads as "not drifted", which is the wrong way to be wrong.
- ☑ The four commands now **render** that envelope. Their decision tables name the field each
  row reads, so they document what the script computed instead of instructing a recompute;
  `done`'s gate is `done_gate.passes` with `failing` printed verbatim on refusal.
- ☑ Two deliberate nulls: `verdicts.*.verdict: null` is *no verdict on record*, never FAIL;
  `done_gate.passes: null` is *not machine-checkable* (spike closes on prose).
- ☑ `scripts/tests/forge-state.test.py` — 68 cases: every status, every tier and the
  precedence, drift present/absent, five schema violations, a missing `.forge/runs/`, both
  verdict kinds, the gate per tier, and the CLI end to end. Wired into ci.yml.
- ☑ Triage gains a signal only determinism makes possible: **frontmatter that does not
  validate**. The heartbeat skill now describes spec-health as "`forge-state.py` + a fixed
  rendering", with the model needed only for the digest prose.

`run-report.py` is untouched and still owns per-run questions (trajectory, tokens, cost,
agent-reported drift events). Two scripts, two questions; merging them would put per-run
cost into a per-feature envelope.

## Phase 19 — Remove the second scaffolding path (added 2026-09-20)

`springboot-scaffold` hand-generated a whole Spring project from a 741-line `scaffold.sh`,
in direct contradiction of the contract everything else depends on: generation goes through
the root `copier.yml`, never anywhere else. The output had no `.forge/manifest.json`, so a
project born that way had no recorded template version, no `copier update` path and no
wiring to the shared gates — **pillars 5 and 6 bypassed at the moment of creation**, which
is the worst possible moment, and silently.

It was also dead-wired and broken, which is why nobody had noticed: no command or agent ever
referenced it (only two sibling skills pointed at it for JVM-vs-TS disambiguation), it
`cp`'d its output to a `/mnt/user-data/outputs/` sandbox path under `set -euo pipefail` — so
on any real machine it exited non-zero *after* generating — and it instructed the model to
deliver the result with `present_files`, a tool Claude Code does not have. Its pins (Boot
4.0 / Modulith 2.0) had also drifted a full major from `kotlin-springboot`'s Maven reference
(3.4.x / 1.3.x), and that reference's pins were literal `x` placeholders that Maven cannot
resolve — a broken pom for anyone who copied it.

Resolution: **delete the generator, keep the routing.** A thin copier wrapper was the other
option and does not fit — copier produces a whole project, while the real use case the skill
named is a *second service inside an existing monorepo*, which no generator covers. The
skill is now routing plus module conventions: `/wellforge:new` for a new project,
`/wellforge:adopt` for an existing one, and a by-hand procedure (inherit parent versions,
root pointer task, wire the gate with a new `working-directory`) for the monorepo case. The
Maven reference's fake pins became `${property}` references with a note naming the shipped
preset as the source of truth — read the pin, don't recall it.

## Order & dependencies

```
P0 ─► P1 (spec) ─► P2 (agents) ─► P3 (orchestrator) ─► P7
        └────────► P4 (scaffolder) ─► P5 (gates) ─► P6 (lifecycle) ─► P7
```

P1+P4 can start in parallel after P0. Total: ~3 weeks of focused effort.

## Risks

- **Copier requires Python tooling** on dev machines → mitigate: install via `mise`/`uv`,
  document in onboarding; fallback is `npx giget` + custom diff (worse, avoid).
- **Template sprawl** → the pilot rule capped shipped presets at 2. A deliberate third,
  `pulumi-gcp-ts` (template v0.7.0), was added because an IaC path is orthogonal to the two
  app stacks and reuses the existing Node gate — it doesn't carry the sprawl risk. The bar
  for a fourth stays high. Phase 12 template extraction still deliberately writes **org-owned**
  templates (outside the WellForge repo, no upstream PR) — adoptions enrich the team's own
  catalog, not WellForge's shipped presets.
- **Agent role bleed** (PO writing code) → explicit "must not" lists in agent prompts,
  checked during pilot.
- **Gates too strict at first** → start thresholds at current-reality levels, ratchet up
  via `gates/` PRs; a gate everyone overrides is worse than no gate.
- **Claude Code plugin API churn** → plugin format is markdown-based and stable; keep
  hooks POSIX-sh portable.
