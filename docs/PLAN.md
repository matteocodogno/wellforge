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
version not yet bumped for these.

## Phase 13 — Loop engineering: parallel worktree isolation (added 2026-07-06)

Motivated by O'Reilly's "loop engineering" (five components: automations, worktrees, skills,
plugins/connectors, subagents). Audit found WellForge already ships four — skills, verifying
subagents, connectors, external state — plus the article's "stay the engineer" spine (human
gates + rigor tiers). Two genuine gaps: **worktree parallel-safety** (this phase) and
**scheduled "heartbeat" automations** (deferred, see below).

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

## Phase 14 — Loop engineering: heartbeat automations (drafted 2026-07-06; 14a + 14b built 2026-07-06)

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
  correctly **absent** for `rigor=spike`; all three workflow files are valid YAML. **Pending
  release**: the reusable `heartbeat-report.yml` only resolves once **`gates-v6` is tagged** — a
  generated project's `@gates-v6` ref 404s until then. Full E2E (a scheduled run opens/updates the
  issue) needs the tag + a real repo → pairs with the Phase 7 pilot. Chose "all three checks +
  weekly" per user; coverage runs too since reusing the whole gate is more DRY than a bespoke
  subset.
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
pieces + scheduling recipes. **Status: all of 14a + 14b built; live scheduling and E2E pair with
the Phase 7 pilot.**

Honest status: **14a + 14b built (2026-07-06).** The deterministic heartbeats (gate, template-drift)
are code-complete and render-/logic-verified but only run once **`gates-v7` is tagged** and a real
scheduled run fires — pairs with the Phase 7 pilot. The agentic heartbeats (fleet, spec-health) ship
as the runnable data step (`fleet-triage.sh`) + command (`/wellforge:triage`) + scheduling recipes;
**live cron is the org's infrastructure, deliberately not auto-enabled** — the vehicle is a Claude
Code routine, which must degrade to `gh`/API auth in headless runs (interactive MCP servers may be
absent), and cadence/thresholds still want the pilot's real signal. 14b was built ahead of the pilot
at the user's request; the pilot will confirm whether the agentic layer earns its keep over the
deterministic heartbeats alone.

## Order & dependencies

```
P0 ─► P1 (spec) ─► P2 (agents) ─► P3 (orchestrator) ─► P7
        └────────► P4 (scaffolder) ─► P5 (gates) ─► P6 (lifecycle) ─► P7
```

P1+P4 can start in parallel after P0. Total: ~3 weeks of focused effort.

## Risks

- **Copier requires Python tooling** on dev machines → mitigate: install via `mise`/`uv`,
  document in onboarding; fallback is `npx giget` + custom diff (worse, avoid).
- **Template sprawl** → hard rule: max 2 presets until Phase 7 proves the model. Phase 12
  template extraction deliberately writes **org-owned** templates (outside the WellForge repo,
  no upstream PR) precisely to keep this guardrail — adoptions enrich the team's own catalog,
  not WellForge's shipped presets.
- **Agent role bleed** (PO writing code) → explicit "must not" lists in agent prompts,
  checked during pilot.
- **Gates too strict at first** → start thresholds at current-reality levels, ratchet up
  via `gates/` PRs; a gate everyone overrides is worse than no gate.
- **Claude Code plugin API churn** → plugin format is markdown-based and stable; keep
  hooks POSIX-sh portable.
