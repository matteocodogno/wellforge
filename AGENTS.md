# WellForge

An open platform for **reproducible, standard, fast AI-assisted project setup** for any team.
Every new project currently costs hours of repetitive AI-infrastructure setup; WellForge turns
that into minutes, with a setup that stays upgradeable over time.

## The 6 pillars

1. **Spec-driven framework** — a standardized spec → plan → tasks workflow. Evaluated: BMAD,
   superpowers, Kiro, cc-sdd, Osmani agent-skills. Decision: build a **thin in-house layer**
   (spec-kit-style) packaged in the plugin, so we own it and it doesn't churn under us.
2. **Multi-agent system** — Product Owner, Architect, Designer, Frontend Dev, Backend Dev,
   DevOps, Quality Engineer as Claude Code subagents.
3. **AI orchestrator** — routes work to the right agent(s), enforces the spec workflow,
   coordinates handoffs (PO → Architect → Devs → QE).
4. **Scaffolder + connection layer** — analyzes the product type, recommends a stack, generates
   the scaffold from a versioned template, and guides MCP/CLI connections to ecosystem tools
   (GitHub, CI, cloud, observability) per stack.
5. **Quality gates** — objective, enforceable thresholds shipped with every scaffold: minimum
   coverage, lint/type-check, security scans (SAST), dependency audits. Defined centrally,
   enforced in CI and locally via hooks — never left to individual discretion.
6. **Project lifecycle** — generated projects record which template+version produced them and
   can be **upgraded** when presets evolve (template diff/merge + migration scripts). Without
   this the scaffolder is a snapshot that rots.

## Architecture decision

A Claude Code plugin alone covers pillars 1–3; pillars 4–6 need artifacts that live *outside*
the AI session (versioned templates, CI workflows). WellForge is therefore three layers:

| Layer | Vehicle | Covers |
|---|---|---|
| `wellforge-plugin/` | Claude Code plugin: skills, agents, commands, hooks, MCP | Pillars 1, 2, 3 + local gate enforcement |
| `copier.yml` + `templates/` | [Copier](https://copier.readthedocs.io) monorepo template (chosen for first-class `copier update` re-templating) | Pillars 4, 6 |
| `.github/workflows/` + `gates/` | Reusable GitHub Actions workflows + central thresholds/SAST configs, referenced (not copied) by scaffolds | Pillar 5 |

`/wellforge:new` is the front door: interview → stack recommendation → `copier copy` →
build verification → connection checklists → first spec. `/wellforge:upgrade` re-runs
`copier update` against the recorded template version with AI conflict resolution.
`/wellforge:orchestrate` drives the full agent pipeline on a goal.

**Rigor tiers** (cross-cutting, `rigor-tiers` skill): `spike`/`mvp`/`production` match
ceremony to stakes — `/wellforge:spike` is the main-loop fast lane (no agents, advisory
gates); `--mode` tunes orchestrate/implement; `/wellforge:promote` graduates a feature or
the project up a tier, paying the deferred rigor. Defer-don't-lower: a lower tier is tracked
debt, raised only via promote (production only on an eval PASS), and a security floor blocks
in every tier. Tier is a copier answer (manifest) + spec/brief frontmatter + command flag.

## Repository layout

`ls` shows it; two things it will not tell you:
- The reusable gate workflows must live in `.github/workflows/` — GitHub only resolves
  `workflow_call` from that path.
- `wellforge-codex-plugin/` is GENERATED (`adapters/codex/generate.py --package`) and CI
  diffs it against a fresh run — never edit it by hand.

## Current state (2026-09)

- **All 6 pillars built** (Phases 0–6 ☑ — per-phase detail and honest deviations in
  `docs/plans/PLAN.md`). Lifecycle E2E-tested: scaffold v0.1.0 → template change → `copier
  update` → zero conflicts.
- **Rigor tiers shipped** (all 3 phases ☑ — `docs/plans/PLAN-rigor-tiers.md`): spike/mvp/production
  across plugin, gates and templates.
- Latest tags: `v0.11.0` (template series, PEP440 — what copier resolves), `gates-v14` (gate
  workflow pin series), `plugin-v2.58.0` (plugin series) and `cli-v1.5.2` (the `wellforge`
  CLI + its Homebrew formula) — four series, the last three invisible to copier by design;
  plugin `2.58.0`, CLI `1.5.2`. **This is the one line in this file that states current
  versions**; `check-docs.py` asserts it against `plugin.json`, `scripts/wellforge` and
  `Formula/wellforge.rb`, and refuses any version claim newer than those files anywhere in
  the docs. Every other version in this file is history and stays as written. A self-CI workflow
  (`.github/workflows/ci.yml`) lints the repo's own commits + smoke-tests all three presets;
  it runs on `origin` (`github.com/matteocodogno/wellforge`, public). It was green on `main`
  from 2026-08-17 until 2026-09-21, then **red for four consecutive pushes without anyone
  noticing**, because the only two jobs failing were the two that do not block a branch push:
  the advisory `formula` job and, briefly, a `cli` job nobody reads on a green-looking PR.
  `release-guard` reads `needs.formula.result` explicitly, so the next tag would have been
  the first time either was heard — which is the failure mode this repo exists to prevent.
  Green again since `9fa14c3` (2026-09-22). **Check the run, do not assume the streak.**
  The four series move independently: a `vX.Y.Z` release does NOT carry a `gates_ref` bump to
  existing projects (recorded answer + `--skip-answered`) — `/wellforge:upgrade` bumps it as
  an explicit, raise-only step. Read `docs/VERSIONING.md` before cutting any release: it
  covers which series to bump, why they are separate, and the never-tag-two-series-on-one-
  commit rule. The plugin's version lives in four places that must agree (`plugin.json`,
  `marketplace.json`'s `version` and `source.ref`, AGENTS.md) — `check-docs.py` fails CI
  otherwise, because a teammate silently installing a different plugin than this repo
  describes is not a failure anything else would report.
- **Phases 16–40** (per-phase detail in `docs/plans/PLAN.md`): parallel-safety
  (`worktree-isolation`; per-checkout databases from template `v0.10.0`, ADR 0002),
  self-critique, TDD, grilling + ledger files, the domain glossary, retro,
  improve-architecture, convergence rules for long runs (`rigor-tiers`), and the Codex
  adapter + native Codex plugin — whose live-session pass (`adapters/codex/SMOKE-TEST.md`)
  is still open.
- **Outstanding** (Phase 7 pilot): full `mise run install/build/test` on a generated project
  and its gates green in **that project's** CI (wellforge's own repo and CI are green — what
  is unproven is a scaffold pushed to GitHub and passing `quality-*.yml` end to end),
  threshold calibration, v1.0.0 cut.

## Conventions

- Plugin agents/commands/skills are Markdown with YAML frontmatter (Claude Code plugin format).
- Generation goes through the ROOT `copier.yml` (`--data preset=<name>`), never
  `templates/<preset>/` directly; scaffolded projects carry `.forge/manifest.json`
  (template, version, answers) — the upgrade contract, never edit either by hand.
- No hidden copy-time-injected answers (e.g. dates) in templates — copier doesn't persist
  `when: false` answers and every future `copier update` would conflict (learned the hard way).
- Template releases: repo-wide `vX.Y.Z` tags, presets in lockstep; semver = patch cosmetic /
  minor additive / major needs `_migrations`. Bump the `template_version` default in the
  release commit.
- Quality thresholds live in the gate workflows' `env` blocks — changed only via PR to
  `gates/`/`.github/workflows/`; templates call them pinned to `gates-v*`.
- Gates are referenced, never copied — with **one guarded exception**: the eval rubric. A
  scaffolded project has no `gates/` on disk, so the in-session evaluator had no rubric to
  read and `/wellforge:eval` failed there (which also blocked `done` for every `production`
  feature). The plugin ships a byte-identical mirror at
  `wellforge-plugin/config/eval-rubric.yml`; `gates/configs/eval-rubric.yml` stays the source
  of truth, and CI's `rubric-sync` job fails if they drift. Change the central one, then
  `cp` it across in the same commit.
- Parallel implementation is worktree-isolated, per the **`worktree-isolation` skill** (the
  authority; `implement`/`orchestrate` delegate to it). Its rule: **a worktree touches nothing
  outside itself except by explicit allowance** — a worktree isolates the *checkout*, not the
  databases, ports, containers, credentials or migration counter the project also reaches, so a
  shared-state **preflight** runs before any batch of ≥2 and an unclassified class means
  sequential dispatch, not a gamble. Gitignored env files are **carried in and verified** (env
  that resolves to empty in a worktree looks exactly like broken code — that's an **environment
  fault**, reported, never fixed in code). Independence is judged on the **effective graph**:
  declared `deps:` ∪ `touch:` overlap, globs included. Each agent commits on its own branch and
  does not touch `tasks.md`; branches integrate by rebase + `--ff-only`, checkboxes reconcile
  centrally, and a conflict means a wrong edge (a "collision"), surfaced like drift. Set
  `worktree.baseRef: "head"`. Solo/sequential batches stay in the main tree.
- **This repo does not version `.forge/runs/`** — a deliberate deviation from the shipped
  default, don't "fix" it. The `observability` skill keeps the semantic `*.json` traces
  committed and all three templates still do, because in a *generated* project they are the
  audit trail and the evaluator's trajectory evidence. Here they are local-only: wellforge is
  tooling, rarely evals itself, and `specs/NNN-slug/eval-report.md` already carries the
  readable verdict. Traces stay on disk, so `/wellforge:status` and `run-report.py` work.
- Every artifact-producing agent (and the main-loop `spec`/`plan`/`tasks` commands) runs
  **one** self-critique pass before handing over, per the **`self-critique` skill** (the
  authority; agents and commands delegate to it). It is a floor-raiser, not a gate: one pass
  never a loop, it never sets `status:` or checks a box, and it is never evidence in a QE or
  eval verdict — independent verification stays the authority. Off at the `spike` tier.
- `frontend-dev` and `backend-dev` implement **test-first**, per the **`tdd` skill** (the
  authority; the agents delegate to it): one behavior per cycle, the test seen to fail *on
  the assertion* before the code exists, the least code to green, refactor on green. A test
  that passes on its first run is suspect until the behavior is broken on purpose.
  Migrations, generated code and wiring are exempt from their own test, never from being
  exercised by one. Like self-critique it is a discipline, not a gate — the `TDD:` line is
  never evidence in a QE or eval verdict. Off at the `spike` tier; `devops` is not wired.
- The default interview stays **batched, two rounds at most** (`spec`, `new`). The deep one
  is opt-in and follows the **`grilling` skill** (the authority; `/wellforge:grill-me` and
  `/wellforge:spec --grill` delegate to it): read before asking, one question at a time,
  parents before children, a recommendation with every question, and a decision ledger
  where *Delegated* is never recorded as *Decided*. Main loop only — never in a subagent,
  never inside `orchestrate`, not at the `spike` tier. It approves nothing and never edits
  an approved artifact: there its output is proposed amendments, routed as drift.
  **The ledger is a file**, written as each decision resolves: `.forge/grill/<slug>.md` for
  an idea, `specs/NNN-slug/ledger.md` for a feature, and moved beside the spec once one
  exists. `/wellforge:spec --ledger` and `/wellforge:orchestrate --ledger` read it — a
  path is the only thing an agent that cannot see the conversation can be handed.
- **The domain glossary is `.claude/context/glossary.md`, governed by the
  `domain-modeling` skill** (the authority): one word per concept, one concept per word, a
  definition that states where the thing begins and ends, and a stress test (boundary,
  identity, cardinality, time, absence) before a term is written. **Only the main loop
  writes it** — `/wellforge:grill-me --docs` as each term resolves, `/wellforge:spec` and
  `orchestrate` on a yes; `product-owner`, `architect` and the dev agents use its terms and
  return *glossary candidates*. It is optional (every instruction says "if present") and
  created lazily, never scaffolded empty. It is injected into every session, so it stays
  small. A sharper term that contradicts an approved artifact is drift, not an edit.
- **`/wellforge:retro` improves the environment, never the code, and never by itself.**
  Every finding cites evidence (a quoted line, a trace entry, a command and its output);
  recurrence ranks it, and at most five are reported. The fix comes from the strongest rung
  that fits — remove the cause, then a mechanism, then a document read on demand, and a
  line in `CLAUDE.md`/`AGENTS.md` only when nothing lower works, because that rung is paid
  for in every session and depends on being read. It never proposes weakening a gate or
  re-tiering an agent on one feature, never commits, and files an upstream issue only on an
  explicit yes. (Not to be confused with the *retro plan* `/wellforge:promote` writes.)
- **`/wellforge:improve-architecture` proposes refactors; it never performs one.** Evidence
  is gathered deterministically first (git co-change, `collision_events` / `drift_events`
  from the run traces) and handed to the `architect`, whose **architecture review mode** is
  the one case where it works without a spec. The lens is module depth — a small interface
  over a lot of behavior. At most five candidates, each with evidence; one taken forward at
  a time and designed two or three ways plus "leave it alone"; the chosen design goes to
  `/wellforge:orchestrate`'s refactor pipeline and the decision to `adr-writer`. It writes
  one file, `docs/architecture/review-<date>.md`. A shape an ADR chose is not a candidate
  unless the ADR's own reasoning no longer holds; no rewrites; no relaxing a boundary to
  remove friction.
- **Before any tag in any series: `mise run check`** (`scripts/check-all.sh`) — every
  self-test in this repo behind one exit code. **Red means no tag.** It is a precondition in
  `scripts/release-cli.sh` and `/wellforge:release`, the committed `gates/hooks/pre-push`
  runs it when a push carries a release tag (branch pushes stay fast), and CI's
  `release-guard` job requires every job green on the tag — that last one cannot be
  bypassed. A tag whose CI is red is **deleted and re-cut, never left**
  (`docs/VERSIONING.md`). This exists because `plugin-v2.49.0` and `cli-v1.5.0` were tagged
  from a tree with seven failing cases: nothing was weakened, the suites were simply not all
  run. Add a new suite to `scripts/check-all.sh` and every one of those paths picks it up —
  `/wellforge:doctor --tests` calls it too, rather than keeping a second list that already
  drifted once.
- **Git policy — non-negotiable, here and in every WellForge repo (incl. generated ones):**
  **linear history** (no merge commits — rebase onto `main`, integrate `--ff-only`, PRs squash
  or rebase) and **Conventional Commits**. Four enforcement layers: local config
  (`merge.ff=only`, `pull.rebase=true`), committed hooks (`gates/hooks/{commit-msg,pre-merge-commit}`),
  CI gates (`commit-lint.yml`, `linear-history.yml` — called at *every* rigor tier), and branch
  protection (`required_linear_history`, `allow_merge_commit=false`). Run
  `./scripts/setup-git-policy.sh` once per clone (generated projects: `mise run git-policy`).
- **Architecture decisions live in `docs/adr/`, indexed one line each under
  `## Architecture decisions` at the end of this file.** The `adr-writer` agent appends that
  line itself. Read the index before changing something an ADR constrains; read the ADR
  before overturning it.
- **This repo has no `CLAUDE.md`** — `AGENTS.md` is the one context file, read natively by
  Claude Code (≥ 2.1.277) and Codex. Generated projects still ship a `CLAUDE.md` that
  imports `AGENTS.md`; that is the templates' contract, not this repo's.
- All text/docs in English. WellForge is **MIT licensed** (see `LICENSE`) and developed
  in the open; "internal" here only ever described the audience — the team this was
  built for — never the licence. The Formula said `license :cannot_represent # internal
  WellForge tooling`, which made an audience note into a licensing claim that
  contradicted the LICENSE file, plugin.json, the README badge and the public repo.

## Architecture decisions

- [0001] Keep full, trigger-phrase-rich descriptions on the five stack skills — shrinking a description to a one-liner deletes exactly the text routing depends on, because the body isn't read until after selection, and this repo has no eval suite to catch the resulting mis-routing: hono-ts-backend, kotlin-springboot, react-ts-vite, pulumi-gcp-ts, mise keep their full trigger phrases + disambiguation clauses, ratcheted by `wellforge-plugin/config/budget.yml` (see docs/adr/0001-keep-full-stack-skill-descriptions.md)
- [0002] Per-worktree database isolation, derived from checkout path — two actors deriving the same name for what each believes is a private resource (a shared convention, not a unique identity) collide silently until the resource itself disagrees with one of them: spring-kotlin-react and hono-react now derive `WF_DB_NAME`/port/compose project from `sha256(checkout path)`, never a basename or timestamp, primary tree exempted, backed by a `mise run db:guard` task (see docs/adr/0002-per-worktree-databases.md)

<!-- groma:start -->
## Groma

This project uses Groma. Before you scan, inspect, or curate architecture, or change files for a Backlog task, run `groma agent-instructions` and read the guide it names for that job. When it reports a first scan, ask the user whether they want you to curate the architecture. Do not edit Groma-owned architecture files directly.
<!-- groma:end -->
