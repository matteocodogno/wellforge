# Contributing to WellForge

For **people**. `CLAUDE.md` is the brief an AI session reads in this repo; it is not a
contributor guide and this file does not repeat it.

## Setup, once per clone

```sh
git clone git@github.com:matteocodogno/wellforge.git && cd wellforge
./scripts/setup-git-policy.sh    # installs the commit-msg / pre-merge-commit / pre-push hooks
mise run check                   # every self-test in the repo, one exit code
```

`setup-git-policy.sh` is not optional: it sets `merge.ff=only` and `pull.rebase=true` and
installs the hooks that enforce the two rules below. It is idempotent.

**`mise run check` before every push.** It is `scripts/check-all.sh` — the single entry point
every release path already takes as a precondition. Red means no tag, and
`gates/hooks/pre-push` refuses a push that carries a release tag from a red tree. Add
`--with-evals` to include the prompt-layer evals, which cost tokens and are therefore off by
default.

## Where does X go?

| Path | What lives there | A change here is… |
|---|---|---|
| `wellforge-plugin/` | the Claude Code plugin: commands, agents, skills, hooks, `config/`, `.mcp.json` | a **new skill** → `skills/<name>/SKILL.md`; a **new command** → `commands/<name>.md` *and* a row in the plugin README and `doctor.md` |
| `templates/` | the three Copier presets (`spring-kotlin-react`, `hono-react`, `pulumi-gcp-ts`) | a **template fix** → `templates/<preset>/template/…`; never generate from here directly, always through the root `copier.yml` |
| `gates/` + `.github/workflows/` | reusable CI gates and the central thresholds | a **gate threshold** → the `env:` block of the gate workflow, by PR. Never lower one locally — that is the whole point of the gate |
| `adapters/` | the Copilot and OpenCode generators | the plugin is the source; change a prompt there and regenerate — see below |
| `scripts/wellforge` | the `wellforge` CLI and its Homebrew formula | a **CLI fix** → `scripts/wellforge` + a case in its matrix |
| `docs/` | versioning, releasing, installation, migrations, plans | the decision log is `AGENTS.md`; ADRs are `docs/adr/` |

## Adapters: the plugin is the source

Nothing generated is committed: the generators write to a `--out` directory you choose, and
the smoke test generates into a temp dir of its own. What IS committed here is the generator,
its README, and the hand-written pieces it ships (`adapters/copilot/githooks/`).

```sh
uv run --with pyyaml python adapters/copilot/generate.py  --out /tmp/wf-copilot
uv run --with pyyaml python adapters/opencode/generate.py --out /tmp/wf-opencode
uv run --with pyyaml python adapters/smoke-test.py --adapter copilot    # and opencode
```

So the rule is not "do not edit the output" — there is no checked-in output to edit. It is:
**the plugin is the source.** If a Copilot or OpenCode user needs different wording, change
the plugin prompt and regenerate; a fix applied to a generated tree exists on one machine
and nothing reports the divergence. `mise run check` runs both smoke tests, and they are
strict: an unresolved relative link in a skill fails them, which is how a link added to
`quality-gates` for the plugin — where the repo root sits above it — was caught before it
shipped broken to both adapters.

## Versioning

Four independent series — template `vX.Y.Z`, `gates-vN`, `plugin-vX.Y.Z`, `cli-vX.Y.Z` — and
**never two tags on one commit**. Which one your change bumps, and why they are separate, is
[docs/VERSIONING.md](docs/VERSIONING.md); read it before cutting anything. Short version of
the part people get wrong:

- plugin prompt/skill/command/hook change → `plugin-v*`, and the prompt evals must be
  fresh (`scripts/check-evals-fresh.sh`; the pre-push hook enforces it)
- a template file a generated project receives → `vX.Y.Z`, and a
  [PLUGIN-MIGRATIONS](docs/PLUGIN-MIGRATIONS.md) or TEMPLATE-MIGRATIONS entry if a project
  must absorb it
- a gate workflow or threshold → `gates-vN`
- `scripts/wellforge` or the formula → `cli-v*` ([docs/RELEASING-CLI.md](docs/RELEASING-CLI.md))
- **bumping a pinned MCP server version in `.mcp.json` is a plugin PATCH release** — the
  version people run is part of what the plugin is, so it is not a silent edit

## Commits and history

**Conventional Commits** and **linear history**, enforced in four places (local config,
committed hooks, CI, branch protection). Rebase onto `main`; integrate `--ff-only`; PRs
squash or rebase. No merge commits.

## Adding a test

Every executable thing here has a matrix. Add the case to the matrix that owns the
behaviour — one file, next to the cases already there:

| What you changed | Add a case to |
|---|---|
| a Bash-blocking rule | `wellforge-plugin/hooks/scripts/tests/pre-bash-guard.test.sh` |
| a Read/Write/Edit/Grep rule | `…/tests/pre-file-guard.test.sh` |
| the Stop verification hook | `…/tests/stop-verify.test.sh` |
| a lifecycle rule (`status:`, rigor, terminal states) | `…/tests/post-spec-guard.test.sh` |
| SubagentStop telemetry | `…/tests/trace-subagent.test.sh` |
| deterministic feature state | `wellforge-plugin/scripts/tests/forge-state.test.py` |
| run-trace parsing or cost attribution | `…/tests/run-report.test.py` |
| which paths trigger a security review | `…/tests/security-triggers.test.py` |
| a gate script (`run-eval.py`, `check-jacoco.py`) | `gates/scripts/tests/gates.test.py` |
| the `wellforge` CLI | `scripts/tests/wellforge.test.sh` |
| `release-guard` in `ci.yml` | `scripts/tests/release-guard.test.py` |
| a **command or agent prompt** | `wellforge-plugin/evals/` — see [evals/README.md](wellforge-plugin/evals/README.md) |

**Write the case so it fails first.** Every check in this repo has at some point passed
while the thing it guarded was broken; a case you have not seen fail is a case you have not
tested. Mutation-test it: break the behaviour, watch the case go red, restore.

### The evals are OPTIONAL in CI, on purpose

They need an `ANTHROPIC_API_KEY`. **This repo deliberately does not have one**, and no fork
or downstream team should need one: the whole of CI must pass, PRs must merge and tags must
cut without it. When the secret is absent the `plugin-evals` job reports **skipped** — not a
green tick for a job that ran nothing, which is the false signal `release-guard` exists to
catch, and which this job was itself producing until it was fixed.

`release-guard` therefore names `plugin-evals` in its optional set: **skipped is accepted, a
failure is not.** Optional means it may not run; it does not mean its red results can be
ignored.

If anyone enables it: it is **billed to whoever owns the key**, so use a dedicated one with
a spend limit rather than a personal or production key. Measured 2026-09-23, a full pass is
roughly **$10–15** at `--runs 1` and **$30–45** at the default `--runs 3`. CI pins `--runs 1`
and only runs the job when `wellforge-plugin/{commands,agents,skills,evals}` changed; a full
pre-release pass is the `workflow_dispatch` route with the `eval_runs` input. Details and
per-case costs: [evals/README.md](wellforge-plugin/evals/README.md).

**The local path needs no key at all** and is the primary one:

```sh
scripts/check-all.sh --with-evals     # uses your own Claude Code login
```

A green local run records the tree it passed against in `wellforge-plugin/evals/LAST-RUN`,
and `scripts/check-evals-fresh.sh` refuses a `plugin-v` tag whose prompt layer has moved
since — because `commands/`, `agents/` and `skills/` have no other test.

## What a PR must show

- [ ] `mise run check` green (say so; paste the summary line)
- [ ] `check-docs.py` green — it fails on version drift, an unpinned MCP server, a stale
      command/skill count, and a Formula sha that does not match its tarball
- [ ] a regression case for the behaviour you changed, and evidence it fails without the fix
- [ ] a migrations entry when a **project** must absorb the change (the test is in
      [PLUGIN-MIGRATIONS.md](docs/PLUGIN-MIGRATIONS.md): *would a project set up by the older
      plugin be wrong, incomplete or noisy under the newer one?*)
- [ ] both adapter smoke tests pass if you touched the plugin's prompts or skills
- [ ] the right series bumped, or an explicit note that none applies

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md), which also carries the
threat model for the plugin as installed on a developer's machine. If your change touches a
guard, a hook, `.mcp.json`, or what an agent is allowed to read or run, say so in the PR: it
is a security-relevant change even when it looks like a prompt edit.
