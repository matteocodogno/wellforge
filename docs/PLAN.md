# WellForge — Implementation Plan

Status legend: ☐ todo · ◐ in progress · ☑ done

---

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
  `skills/springboot-scaffold/scripts/scaffold.sh` + react-ts-vite setup + mise skill.
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
