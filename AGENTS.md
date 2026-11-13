# WellForge

Reproducible, upgradeable AI-assisted project setup: a Claude Code plugin
(`wellforge-plugin/`), a Copier monorepo template (`copier.yml` + `templates/`) and reusable
CI quality gates (`.github/workflows/` + `gates/`). What it does and why:
`docs/FEATURES.md`; roadmap and per-phase history: `docs/plans/PLAN.md`.

## Commands

- **Verify everything:** `mise run check` (`scripts/check-all.sh`) — every self-test, one exit
  code. `mise run check -- --quick` skips scaffold work. Red means no tag, in any series.
- **One suite:** `bash wellforge-plugin/hooks/scripts/tests/<hook>.test.sh`,
  `python3 wellforge-plugin/scripts/tests/<name>.test.py`, `python3 scripts/tests/<name>.test.py`.
- **Prompt evals (paid):** `mise run check -- --with-evals` (full, records `LAST-RUN`), or only
  what changed: `mise run check -- --eval-case '<glob>' --eval-runs 1`.
- **Scaffold from the working tree:** `uvx copier copy --defaults --trust --vcs-ref HEAD .
  <dir> --data preset=<spring-kotlin-react|hono-react|pulumi-gcp-ts>` (always the ROOT
  `copier.yml`, never `templates/<preset>/`).
- **After any change under `wellforge-plugin/`:** regenerate the Codex package —
  `uv run --with pyyaml python adapters/codex/generate.py --package wellforge-codex-plugin
  --marketplace .agents/plugins/marketplace.json`. CI diffs it against a fresh run.
- **Release:** `mise run release:<plugin|template|cli> -- <patch|minor|major>` or
  `mise run release:gates` (the next N) — plan; add `--execute`, then `--push`. Never by hand.
- **Once per clone:** `mise trust && mise install && mise run setup` (pinned Python + pyyaml in
  `.venv`), then `./scripts/setup-git-policy.sh`.

## Versions

- Latest tags: `v0.13.0` (template series, PEP440 — what copier resolves), `gates-v15` (gate
  workflow pin series), `plugin-v2.62.2` (plugin series) and `cli-v1.5.2` (the `wellforge`
  CLI + its Homebrew formula) — four series, the last three invisible to copier by design;
  plugin `2.62.2`, CLI `1.5.2`. This is the one line that states current versions:
  `check-docs.py` asserts it against `plugin.json`, `scripts/wellforge` and the Formula, and
  `release-cli.sh` rewrites it. Every other version in the docs is history.
- The four series move independently and never share a commit's tag. Read
  `docs/VERSIONING.md` before any release. The plugin version lives in `plugin.json`,
  `marketplace.json` (`version` and `source.ref`) and the line above; `check-docs.py` fails CI
  if they disagree. A tag whose CI is red is deleted and re-cut, never left.
- Template releases: repo-wide `vX.Y.Z`, presets in lockstep, `template_version` default bumped
  in the release commit; project-side notes in `docs/TEMPLATE-MIGRATIONS.md` (plugin:
  `wellforge-plugin/PLUGIN-MIGRATIONS.md`), written in the same commit as the change.
- A `vX.Y.Z` release does not bump `gates_ref` in existing projects (recorded answer +
  `--skip-answered`); `/wellforge:upgrade` does that as an explicit, raise-only step.

## Gotchas

- Reusable gate workflows must stay in `.github/workflows/`: GitHub resolves `workflow_call`
  from nowhere else.
- `wellforge-codex-plugin/` is generated — never edit it by hand.
- No copy-time-injected answers (dates, ports) in templates: copier does not persist
  `when: false` answers, so every later `copier update` would conflict.
- Quality thresholds live in the gate workflows' `env` blocks and change only by PR to
  `gates/` / `.github/workflows/`; templates call the gates pinned to `gates-v*`.
- Gates are referenced, never copied — except the eval rubric: the plugin ships a
  byte-identical mirror (`wellforge-plugin/config/eval-rubric.yml`) because a scaffold has no
  `gates/`. Change `gates/configs/eval-rubric.yml`, then `cp` it across in the same commit;
  CI's `rubric-sync` job fails otherwise.
- This repo does **not** version `.forge/runs/` — a deliberate deviation from the default the
  templates ship (there the traces are the audit trail). Don't "fix" it.
- The plugin's `pre-bash-guard` matches command TEXT: a command, commit message or script whose
  text names a secret file (the dotenv family, keys, `secrets.yml`) is blocked even when it only
  greps for the name. Put such text in a file and pass the path (`git commit -F`, `python3 x.py`).
- `CI is green` is a claim to check, not assume: the advisory `formula` job and the `cli` job
  do not block a branch push, and once stayed red for four pushes unnoticed. `gh run list`.
- This repo has no `CLAUDE.md`: Claude Code (≥ 2.1.277) and Codex read this file. Generated
  projects still ship a one-line `CLAUDE.md` importing `AGENTS.md` (template contract).
- English only. MIT licensed (`LICENSE`); "internal" only ever described the audience.

## Where the rules live

The plugin's process rules each have ONE authority — a skill. Commands and agents delegate to
it; change the rule there, never restate it elsewhere:

| Rule | Authority |
|---|---|
| spec → plan → tasks, status lifecycle, drift | `spec-driven` skill |
| tiers, convergence caps, security floor | `rigor-tiers` skill |
| parallel batches, shared-state preflight, env carry-in | `worktree-isolation` skill |
| one self-review pass before handover | `self-critique` skill |
| test-first in `frontend-dev` / `backend-dev` | `tdd` skill |
| deep interview, decision ledger | `grilling` skill |
| what agents decided for the user (`DECISIONS:` → `decisions.md`) | `spec-driven` skill — enforced by `subagent-decisions-guard.sh` |
| project glossary (main loop writes it) | `domain-modeling` skill |
| linear history + Conventional Commits | `git-policy` skill — enforced by hooks, CI and branch protection |
| gate catalogue and thresholds | `quality-gates` skill |
| template contract | `templates/_shared/CONTRACT.md` |
| done gate conditions | `forge-state.py --explain-gate` |

Mechanical rules belong in a hook or a check, not in prose: if a line here keeps being missed,
move it into `post-spec-guard.sh`, `stop-verify.sh` or `scripts/check-all.sh`.

## Open work

- Phase 7 pilot: a generated project pushed to GitHub with its `quality-*.yml` gates green in
  that project's own CI; threshold calibration; the v1.0.0 cut.
- Codex adapter live-session pass (`adapters/codex/SMOKE-TEST.md`).

## Architecture decisions

- [20260920] Keep full, trigger-phrase-rich descriptions on the five stack skills — shrinking a description to a one-liner deletes exactly the text routing depends on, because the body isn't read until after selection, and this repo has no eval suite to catch the resulting mis-routing: hono-ts-backend, kotlin-springboot, react-ts-vite, pulumi-gcp-ts, mise keep their full trigger phrases + disambiguation clauses, ratcheted by `wellforge-plugin/config/budget.yml` (see docs/adr/20260920-keep-full-stack-skill-descriptions.md)
- [20260920] Per-worktree database isolation, derived from checkout path — two actors deriving the same name for what each believes is a private resource (a shared convention, not a unique identity) collide silently until the resource itself disagrees with one of them: spring-kotlin-react and hono-react now derive `WF_DB_NAME`/port/compose project from `sha256(checkout path)`, never a basename or timestamp, primary tree exempted, backed by a `mise run db:guard` task (see docs/adr/20260920-per-worktree-databases.md)

<!-- groma:start -->
## Groma

This project uses Groma. Before you scan, inspect, or curate architecture, or change files for a Backlog task, run `groma agent-instructions` and read the guide it names for that job. When it reports a first scan, ask the user whether they want you to curate the architecture. Do not edit Groma-owned architecture files directly.
<!-- groma:end -->
