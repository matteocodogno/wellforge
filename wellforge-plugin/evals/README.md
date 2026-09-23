# Prompt-layer evals

Every script and hook in this repo has a regression matrix. `commands/` and `agents/` — most
of what the plugin actually **is** — had none, because a prompt cannot be asserted with
`grep`. These are behavioural: a real Claude session runs the command against a frozen
fixture project, and graders score what it *did*.

## Running them

```sh
# everything (costs money — see below)
claude plugin eval ./wellforge-plugin --scaffold --trust-plugin --no-publish --threshold 0.8

# one case, one run, cheapest useful signal while authoring
claude plugin eval ./wellforge-plugin --case done-mvp-passes --runs 1 --ablation none \
  --scaffold --trust-plugin --no-publish

# through the repo's own entry point
mise run check -- --with-evals
```

**They cost real money.** Each case is N full agent runs against the API, and by default
`--runs 3` in two arms (with and without the plugin). Measured on 2026-09-23: one case at
`--runs 1 --ablation none` cost **$0.41** (`status-rows`) and **$1.23** (`done-production-refuses`).
That is why `check-all.sh` leaves them off unless you pass `--with-evals`, and why the CI job
is separate and optional — see below.

Why the flags:

- `--scaffold` — every case's `scaffold.sh` copies `fixtures/project/` into the run's working
  directory. Runs start in an **empty** throwaway directory, so without it there is no project
  to act on. It runs author-supplied bash, which is why the runner makes you ask for it.
- `--trust-plugin` — answers the first-run trust prompt, which has no answer in CI.
- `--threshold 0.8` — an LLM judge is not a unit test. Demanding 1.0 from three judge votes
  per grader buys a flaky suite that people learn to ignore, which is worse than no suite.

`evals/results/` is gitignored: the cases and the fixture are source, what a given run scored
is not.

## Optional in CI, and why

They need an `ANTHROPIC_API_KEY`. **This repo deliberately does not have one**, and no fork
or downstream team should need one: the whole of CI must pass, PRs must merge and tags must
cut without it. When the secret is absent the `plugin-evals` job reports **skipped** — not a
green tick for a job that ran nothing, which is the false signal `release-guard` exists to
catch, and which this job was itself producing until it was fixed.

`release-guard` therefore names `plugin-evals` in its optional set: **skipped is accepted, a
failure is not.** Optional means it may not run; it does not mean its red results can be
ignored.

If anyone does enable it, three things are worth knowing before they do:

- **It is billed to whoever owns the key.** Measured 2026-09-23: one case, one run, one arm
  cost $0.41 and $1.23. The nine cases in both arms at `--runs 1` is roughly **$10–15 per
  pass**; at the suite default `--runs 3`, roughly **$30–45**.
- **Use a dedicated key with a spend limit**, not a personal or production one. A workflow
  that spends money on every push is one bad loop away from an unpleasant invoice.
- CI pins `--runs 1` and only runs the job when something under
  `wellforge-plugin/{commands,agents,skills,evals}` actually changed. A full pass before a
  plugin release is the `workflow_dispatch` route, with the `eval_runs` input.

**The local path needs no key at all** and is the primary one:

```sh
scripts/check-all.sh --with-evals     # uses your own Claude Code login
```

A green local run records the tree it passed against in `wellforge-plugin/evals/LAST-RUN`,
and `scripts/check-evals-fresh.sh` refuses a `plugin-v` tag whose prompt layer has moved
since — because `commands/`, `agents/` and `skills/` have no other test.

## The fixture project

`fixtures/project/` is a frozen WellForge project with six features in known states, so a
case asserts against something fixed instead of whatever a live repo happens to contain:

| Feature | State |
|---|---|
| `001-checkout-flow` | approved, **production**, plan approved |
| `002-search-filters` | approved, **mvp**, **no plan at all** |
| `003-order-history` | in-progress, production, 3/3 tasks, QE **PASS**, no eval report |
| `004-cache-spike` | **spike**, a `brief.md`, already done |
| `005-legacy-payments` | **superseded** by 001 |
| `006-wishlists` | **draft**, untouched for 40 days |

It is validated by the plugin's own state layer, not by eye:

```sh
cd fixtures/project && uv run --with pyyaml python ../../../scripts/forge-state.py
```

That must report zero schema problems. It caught four errors in the fixture when it was
written — a missing `spec:` in `plan.md` and `tasks.md`, a `tasks.md` with no frontmatter at
all, and a run trace whose `schema` and `agents` shape were both wrong, which silently meant
`003`'s QE verdict did not count. A fixture nobody validates is a test that asserts against
a fiction.

A case that needs a *different* state edits its own copy in `scaffold.sh` — see
`tasks-draft-plan-stops` (flips 001's plan to draft) and `done-mvp-passes` (drops 003 to mvp).
Never edit the shared fixture for one case.

## Adding a case

```
evals/<case-name>/
├── prompt.md          # frontmatter: execution settings. body: what the user types.
├── case.yaml          # identity + context (the scaffold). Nothing else.
├── scaffold.sh        # copies the fixture in; then mutate it for this case if needed
└── graders/
    └── <name>.md      # one grader per file
```

1. **`prompt.md`** — YAML frontmatter then the prompt body. Useful keys: `name`,
   `max_turns`, `allowed_tools`, `runs`, `tags`. **An unknown key is a hard error**, not a
   warning, so do not invent fields.
2. **`case.yaml`** — `schema_version: "1.1"`, `name`, `tags`, and `context.scaffold_script`.
   Execution settings live in `prompt.md` and only there; one key, one home.
3. **`graders/*.md`** — frontmatter `type:` is one of `regex`, `tool_used`, `tool_order`,
   `file_exists`, `llm`, `baseline`. Prefer a deterministic grader where the claim is
   deterministic: whether a file exists, whether `status: done` was written. Reach for `llm`
   only for judgement — "did it explain why it refused".
4. **Run it once with `--runs 1 --ablation none`** before you commit it, and read the
   explanation of every grader. A grader that passes for the wrong reason is the normal
   failure here: a regex that matches the prompt echoed back, an `llm` rubric so loose that
   any answer passes.
5. **Make it fail first.** Break the behaviour the case is about and watch it go red. A case
   you have never seen fail has not been tested — that applies to these exactly as it does to
   the shell matrices.

Point a grader at a file with `target: {source: file, path: "specs/…/tasks.md"}`; at the
whole session with `target: trace`; at the answer with `target: last_message` (the default).

## What is covered

| Case | The claim |
|---|---|
| `status-rows` | every fixture reports the right state, and a sensible next command |
| `tasks-mvp-no-plan` | at mvp, a missing plan does **not** stop tasks; `## Architecture notes` is written |
| `tasks-draft-plan-stops` | at production, a **draft** plan **does** stop tasks |
| `done-production-refuses` | production done refuses without an eval, and names what is missing |
| `done-mvp-passes` | the same feature at mvp closes on tasks + QE PASS |
| `eval-never-closes` | `/wellforge:eval` never writes `status: done` — that is `done`'s job |
| `evaluator-catches-mock-only-test` | a test that only asserts a mock scores below the bar, cited by filename |
| `implement-announces-downgrade` | `--mode mvp` on a production feature announces the downgrade **first** |
| `owasp-pass-with-notes` | "PASS WITH NOTES" is recorded as `PASS`, notes kept, no third verdict |
