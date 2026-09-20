# WellForge improvement prompts

One self-contained prompt per suggestion, in priority order. Each is meant to be pasted
into a Claude Code session opened at the wellforge repo root. They assume the repo
conventions (Conventional Commits, linear history, `wellforge-plugin/` layout, `ci.yml`
running the plugin self-tests) and each ends with the same closing block so the result is
verified and committed the same way.

Suggested order: 2 → 3 → 4 → 1 → 5 → 6 → 7 → 9 → 8 → 10. Items 2 and 3 are the
foundation the others build on; 10 is a template change and belongs in its own `vX.Y.Z` cut.

---

## 1. Prompt-level evals for commands, agents and skill descriptions

```
Add a plugin eval suite for wellforge-plugin so that command and agent BEHAVIOR is tested,
not only the hook and Python scripts.

Context: the plugin has deterministic tests (hooks/scripts/tests/*.test.sh,
scripts/tests/run-report.test.py, scripts/check-routing.py, scripts/check-docs.py) but zero
tests for what the prompts in commands/ and agents/ actually do. Recent bugs that a prompt
eval would have caught: /wellforge:tasks refused every mvp feature because it gated on a
plan.md that mvp never has; four commands set `status: done` themselves instead of routing
through /wellforge:done; the evaluator read a rubric path that does not exist in scaffolded
projects.

Do this:
1. Read `claude plugin eval --help` and the current docs for plugin eval suites (use the
   claude-code-guide agent if needed). Do not invent the format.
2. Create wellforge-plugin/evals/ with a fixture project under evals/fixtures/ containing a
   minimal .forge/manifest.json and a specs/ directory with features in known states:
   001 production spec approved + plan approved + no tasks; 002 mvp spec approved + no plan
   + no tasks; 003 in-progress with all tasks checked, QE PASS in .forge/runs/, no eval;
   004 spike brief done; 005 spec superseded; 006 draft parked for 40 days.
3. Write eval cases with assertions for at least: /wellforge:status emits the correct row
   and next command for each of the six fixtures; /wellforge:tasks on 002 does NOT stop on
   the missing plan and writes the `## Architecture notes` section; /wellforge:tasks on 001
   with plan status draft DOES stop; /wellforge:done on 003 at production refuses (no eval)
   and at mvp passes; /wellforge:eval never writes `status: done`; the evaluator, given a
   test file that only asserts a mock, scores test quality below the rubric bar and cites
   the file; /wellforge:implement --mode mvp on a rigor: production feature announces the
   downgrade before doing anything.
4. Run /skill-doctor (or the equivalent) over every skills/*/SKILL.md description and fix
   what it flags without changing when a skill should trigger.
5. Add the eval run to .github/workflows/ci.yml next to the existing self-tests, as a
   separate job that can be marked required later.
6. Document how to add a case in wellforge-plugin/evals/README.md and add a row to the
   plugin README structure table; scripts/check-docs.py must stay green.

Closing block: run every self-test (check-routing, check-docs, the three hook matrices,
run-report tests, and the new evals). Bump the plugin version (minor). Commit with
Conventional Commits, one logical commit per step where sensible, no merge commits.
Report what the evals caught, if anything, and what remains untested.
```

---

## 2. Deterministic lifecycle state (`forge-state.py`)

```
Make feature lifecycle state deterministic and machine-readable, so status, triage, done and
promote stop re-deriving it with the model.

Context: /wellforge:status, /wellforge:triage, /wellforge:done and /wellforge:promote each
have the model read specs/*/spec.md frontmatter, count tasks.md checkboxes, and call
scripts/run-report.py --json to find QE/eval verdicts. That is slow, costs tokens on every
heartbeat, is not testable, and cannot reject a typo like `status: doen`. The heartbeat skill
already says discovery should be deterministic and only judgment agentic.

Do this:
1. Read skills/spec-driven/SKILL.md (status lifecycle, frontmatter fields, drift rule),
   skills/rigor-tiers/SKILL.md (tier precedence, done gate per tier),
   skills/observability/SKILL.md (run trace schema, verdicts), commands/status.md,
   commands/triage.md, commands/done.md, commands/promote.md, and scripts/run-report.py.
2. Write wellforge-plugin/config/spec-frontmatter.schema.json: a JSON Schema for spec.md,
   plan.md, design.md, tasks.md and brief.md frontmatter as the spec-driven skill defines
   them (id, slug, status enum incl. superseded/archived, rigor enum, created, approved,
   done, superseded_by, archive_reason). The skill stays the human-readable authority; the
   schema must match it exactly and check-docs.py should fail if the enum values in the
   skill and the schema diverge.
3. Write wellforge-plugin/scripts/forge-state.py (stdlib only, pyyaml optional like
   run-report.py) that walks specs/, validates every frontmatter against the schema, counts
   tasks (total/checked, using the tasks.md format from the skill), computes drift (spec or
   plan newer than tasks.md, by git log date with mtime fallback), joins the latest QE and
   eval verdicts and their timestamps from .forge/runs/ (reuse run-report.py's loaders, do
   not duplicate them), resolves the effective rigor tier per the precedence rule, and emits
   `--json` as one envelope: {version:"forge-state/v1", generated, features:[{slug, kind
   (spike|feature), status, rigor, artifacts:{...}, tasks:{total,checked}, drift:{...},
   verdicts:{qe:{...}, eval:{...}}, done_gate:{tier, passes:bool, failing:[...]},
   problems:[...schema violations...]}]}. Also a human table with no flag.
4. Rewrite commands/status.md and commands/triage.md so the model runs
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py --json` once and renders from it;
   the decision tables in those commands become documentation of what the script computes,
   not instructions to recompute it. Rewrite commands/done.md so the gate check is
   `done_gate.passes` for the resolved tier, with `failing` shown verbatim on refusal.
   commands/promote.md uses the same envelope for its precondition checks.
5. Add scripts/tests/forge-state.test.py with fixtures covering every status, every tier,
   drift present/absent, a schema violation, missing .forge/runs/, and both verdict kinds.
   Wire it into ci.yml with the other self-tests. Add the script to commands/doctor.md's
   checks and to the plugin README table.
6. Update the heartbeat skill so the spec-health heartbeat can be described as
   "forge-state.py + a fixed rendering", with the model needed only for the digest prose.

Closing block: run every self-test. Bump the plugin version (minor). Conventional Commits,
linear history. Report the envelope shape and any place where a command still asks the
model to derive state that the script now provides.
```

---

## 3. Mechanically enforce the `done` and `rigor` transitions

```
Turn the "single guarded place" for `status: done` and the "defer, don't lower" rule for
`rigor:` into hooks, not prompt promises.

Context: every command was rewritten so only /wellforge:done sets `status: done` and only
/wellforge:promote raises `rigor:`. Nothing enforces it: any Edit to specs/*/spec.md can
flip either field. hooks/scripts/stop-verify.sh already enforces the drift rule mechanically;
extend the same approach. This depends on scripts/forge-state.py (its done_gate output). If
that script does not exist yet, stop and say so.

Do this:
1. Add hooks/scripts/post-spec-guard.sh registered as a PostToolUse hook on
   Write|Edit|MultiEdit in hooks/hooks.json. It runs only when tool_input.file_path matches
   specs/*/(spec|brief).md inside a WellForge project (specs/ or .forge/ present), else
   exits 0 immediately.
2. Behavior: diff the file's frontmatter before/after (git show HEAD:<path> vs the new
   content; if the file is untracked treat "before" as empty). If `status` changed to
   `done`, run forge-state.py --json for that slug and, unless done_gate.passes is true for
   the resolved tier, block (exit 2) with the `failing` list and "run /wellforge:done <slug>".
   If `rigor` moved to a lower tier (production > mvp > spike), block with "lower rigor is
   deferred debt: use --mode for one run, or a new feature; promote is raise-only". If
   `status` moved backwards from done to anything, block unless the new status is
   superseded or archived. Any frontmatter that fails the schema blocks with the violation.
   Everything else passes silently. The hook must never block a Write that is creating a
   brand-new spec with status draft.
3. Use JSON hook output where it makes the message clearer, otherwise exit 2 + stderr, and
   keep the same defensive style as the other hooks (jq missing → see item 4's rule if
   already implemented, else exit 0 with a stderr warning).
4. Add hooks/scripts/tests/post-spec-guard.test.sh driving the real hook with fixture
   projects: legal draft→approved, approved→in-progress, in-progress→done with gate
   passing (allowed), with gate failing (blocked), rigor production→mvp (blocked),
   mvp→production (allowed), done→superseded (allowed), done→draft (blocked), new spec
   file (allowed), edit outside specs/ (no-op). Wire into ci.yml.
5. Update commands/done.md and commands/promote.md to state that the hook is the mechanical
   backstop and what the model must do when it fires. Add the hook to the README hooks
   table and to commands/doctor.md's hook listing (hook count changes).

Closing block: run every self-test. Bump the plugin version (minor). Conventional Commits,
linear history. Report any legitimate flow that the new hook would block, with the
proposed carve-out.
```

---

## 4. Fail closed on missing `jq`, and use "ask" instead of "block" where a human decision is the right answer

```
Harden the hook guards: fail closed when their dependency is missing, and downgrade
hard blocks to permission prompts where a human decision is the right answer.

Context: every hook in hooks/scripts/ starts with `INPUT=$(cat)` and parses it with jq. If
jq is not installed, pre-bash-guard.sh gets an empty COMMAND and `exit 0`s: the guard
silently disables itself. Separately, the guards use exit 2 (hard block) for operations
where the better outcome is "ask the human right now in the same turn": git reset --hard,
force-deleting a branch, DROP TABLE against a dev database, git clean -fdx. Claude Code
PreToolUse hooks can return JSON with hookSpecificOutput.permissionDecision set to
"allow" | "deny" | "ask" plus permissionDecisionReason.

Do this:
1. Read the current Claude Code hooks reference for the JSON output format (use the
   claude-code-guide agent). Confirm "ask" is supported for PreToolUse and what the user
   sees.
2. In pre-bash-guard.sh and pre-file-guard.sh: if jq is missing, exit 2 with
   "wellforge guard unavailable: jq not installed (brew install jq)". In every other hook
   (advisory ones) keep exit 0 but print a one-line stderr warning. Add a jq check to
   commands/doctor.md as a FAIL (not WARN) because the guards depend on it, and to
   session-start.sh as a single stderr line when missing.
3. Reclassify pre-bash-guard.sh rules into three buckets and document the rationale at the
   top of the file: DENY (never in an agent: rm -rf of root/home, piping remote scripts to
   a shell, reading secret files, force push without lease); ASK (destructive but sometimes
   right: git reset --hard, git branch -D, git clean -fdx, DROP/TRUNCATE against a database,
   git push --force-with-lease); ALLOW (everything else). Emit JSON for ASK with a
   reason that says what is destroyed. DENY may stay exit 2 or use "deny"; pick one and be
   consistent.
4. Update hooks/scripts/tests/pre-bash-guard.test.sh: the runner must distinguish
   ALLOW / ASK / DENY (parse the JSON when present) and every existing case keeps its
   intent; add the missing-jq case by running the hook with PATH stripped of jq.
5. Update the README hooks row, skills/quality-gates or connections wherever the guard
   behavior is described, and commands/doctor.md's guard self-check.

Closing block: run every self-test. Bump the plugin version (minor). Conventional Commits,
linear history. Report the final rule table (DENY / ASK / ALLOW) in the commit body.
```

---

## 5. Measure and cap the fixed per-session context cost

```
Measure how many tokens the plugin injects into every session before the user types, and
put a ceiling on it that CI enforces.

Context: 21 skill descriptions, 20 command descriptions and 10 agent descriptions are
loaded into every Claude Code session in every project where the plugin is enabled,
including non-WellForge repos. Descriptions average ~600 characters and the "Trigger
phrases: ..." pattern is much of it. The plugin already owns the right tool for shrinking
them: commands/terse-compress.md with its fact-preservation gate.

Do this:
1. Extend scripts/check-docs.py (or add scripts/check-budget.py) to compute, for
   skills/*/SKILL.md, commands/*.md and agents/*.md, the characters and an estimated token
   count (chars/4 is fine, say so) of each description plus the total. Print a table
   sorted by size and fail when the total exceeds a ceiling stored in config/budget.yml
   (set the initial ceiling at 85% of today's total so the check is green now and rejects
   growth). Also fail on any single description over 1024 characters.
2. Run /wellforge:terse-compress over the ten largest descriptions with a target of
   -30% each, keeping every trigger phrase that decides when the skill fires (the
   safety gate must pass). Do NOT compress bodies, only descriptions. Skills whose
   description is mostly a "do not use when" clause keep that clause.
3. Evaluate, and write the decision down in docs/ (an ADR via the adr-writer agent):
   should the stack skills (hono-ts-backend, kotlin-springboot, react-ts-vite,
   pulumi-gcp-ts, mise) keep full descriptions everywhere, or become one-line descriptions
   that defer to the body? Consider trigger accuracy (item 1's evals, if present) vs.
   the per-session cost in unrelated repos.
4. Add the budget check to ci.yml and to commands/doctor.md --tests. Record the before and
   after totals in the commit body.

Closing block: run every self-test. Bump the plugin version (patch if descriptions only
shrank, minor if the check is new). Conventional Commits, linear history. Report the
before/after table.
```

---

## 6. Record the plugin version in the project and let doctor compare

```
Record which plugin version scaffolded, adopted or last upgraded a project, and make
/wellforge:doctor and /wellforge:upgrade aware of it.

Context: .forge/manifest.json records the template name, version and copier answers, which
is what makes /wellforge:upgrade possible. Nothing records the plugin version, yet the
project's AGENTS.md conventions, the spec-driven file formats, the .forge/runs/ trace
schema and the hooks all change with the plugin. There is no way today to know a project
was set up by plugin 2.20 and is being driven by 2.35.

Do this:
1. Read skills/template-contract/SKILL.md, templates/_shared/CONTRACT.md, copier.yml,
   commands/new.md, commands/adopt.md, commands/upgrade.md, commands/doctor.md and
   skills/observability/SKILL.md.
2. Add a `plugin` object to the manifest contract: {"version": "<plugin.json version>",
   "set_by": "new|adopt|upgrade", "at": "<ISO date>"}. Decide, and document in CONTRACT.md,
   whether this is a copier answer (persisted, would conflict on update) or written by the
   command after generation (preferred, per the "no hidden copy-time answers" convention in
   CLAUDE.md). For adopted projects the same object lives in .forge/adoption.json.
3. new.md and adopt.md write it; upgrade.md updates it and treats a plugin-version jump as
   a first-class step: it reads a new docs/PLUGIN-MIGRATIONS.md (create it) listing, per
   plugin minor, any project-side changes (e.g. .forge/runs/ schema bumps, new hooks
   needing gitignore entries, renamed frontmatter fields) and applies or surfaces them.
4. doctor.md compares the running plugin version to the recorded one: OK when equal, WARN
   when the plugin is newer (with "run /wellforge:upgrade to apply plugin migrations"),
   FAIL when the project is newer than the plugin (someone is on an old plugin).
5. scripts/fleet-status.sh gains a plugin-version column next to the template version.
6. Add the field to the observability run envelope (run traces record the plugin version
   that produced them) and bump the trace schema version accordingly, updating run-report.py
   and its tests to accept both.

Closing block: run every self-test plus the copier smoke test for all three presets. Bump
the plugin version (minor). Conventional Commits, linear history. Report what an existing
project without the field sees from doctor (must be a WARN with the fix, never a crash).
```

---

## 7. Trigger the security and ADR specialists from the task graph

```
Dispatch the owasp-reviewer and adr-writer agents from data in the task graph instead of
relying on the orchestrator remembering them.

Context: agents/owasp-reviewer.md is invoked only when someone thinks of it. tasks.md
already declares `touch:` globs per task and plan.md has structured decision sections.
The security floor is described as non-negotiable in skills/rigor-tiers/SKILL.md, but the
specialist that checks it is optional in practice.

Do this:
1. Read commands/implement.md, commands/orchestrate.md, commands/promote.md,
   agents/owasp-reviewer.md, agents/adr-writer.md, skills/rigor-tiers/SKILL.md,
   skills/spec-driven/SKILL.md (tasks.md format, touch:) and skills/worktree-isolation
   (integration order).
2. Add config/security-triggers.yml: a list of glob patterns whose presence in any
   `touch:` of a batch requires an owasp-reviewer pass before QE (auth/**, **/security/**,
   **/*Controller*.kt, **/routes/**, **/middleware/**, **/db/changelog/**, **/migrations/**,
   **/*.sql, anything matching upload|payment|token|session|password in the path), plus
   an `always_at_tier: [production]` switch. Document the file in skills/quality-gates.
3. In implement.md and orchestrate.md, after integration and before the QE stage: compute
   the union of touched files for the batch (declared touch: plus the actual git diff
   name-only against the feature branch base), match against the triggers, and when matched
   spawn owasp-reviewer scoped to those files. Its findings route like QE failures (code →
   dev agent, spec → PO) with the same 2-round cap. Record the dispatch and verdict in the
   run trace (observability skill: add a `security` verdict alongside qe and eval, bump
   the schema, update run-report.py and forge-state.py if present, and their tests).
4. commands/done.md: at production, a matched batch without a recorded security PASS is a
   failing done-gate condition.
5. adr-writer: in commands/plan.md and the architect agent, when plan.md contains a
   `## Decisions` (or equivalent per the spec-driven format) entry that names an
   alternative rejected, dispatch adr-writer for that decision automatically at production
   and offer it at mvp. Make the ADR file path predictable (docs/adr/NNNN-slug.md) and
   referenced from plan.md.
6. Add eval cases (if item 1's suite exists) or at least a fixture-driven test for the
   glob matching if you implement it as a script.

Closing block: run every self-test. Bump the plugin version (minor). Conventional Commits,
linear history. Report the final trigger list and the cost implication (one extra mid-tier
agent per matched batch).
```

---

## 8. Turn observability into budgets

```
Make the cost and time numbers in .forge/runs/ actionable: per-tier budgets, overrun
flagging in triage, and a fleet-wide view.

Context: hooks/scripts/trace-subagent.sh captures per-agent tokens and model,
scripts/run-report.py estimates cost per run and can compare a run against a control, and
config/model-routing.yml says agents move down a tier "only with evidence". No command
consumes that evidence. scripts/fleet-status.sh only reports template versions.

Do this:
1. Read skills/observability/SKILL.md, skills/rigor-tiers/SKILL.md, skills/heartbeat/
   SKILL.md, scripts/run-report.py and its tests, commands/triage.md, commands/status.md,
   scripts/fleet-status.sh and scripts/fleet-triage.sh.
2. Add budgets to config/rigor-budgets.yml: per tier, a soft cost ceiling per feature (USD)
   and per run, and a wall-clock ceiling per implement batch, plus an
   `advisory_only: true` flag (budgets surface, they never block; heartbeat rule
   "surface, never ship"). Document them in rigor-tiers.
3. run-report.py: add `--budget` output per run and per feature (spent vs ceiling,
   percentage, the agent that consumed the most), and a `--rework` metric: number of
   QE-fail→dev-fix rounds per feature from the trace, which is the "rework loop" signal
   model-routing.yml asks for. Extend the tests.
4. triage.md gains two sections: "Over budget" (feature > 100% of tier ceiling) and
   "Rework hotspots" (agents whose rework rounds exceed a threshold in the last N runs),
   each with the deterministic query that produced it, per the heartbeat skill's
   deterministic-vs-agentic split.
5. fleet-triage.sh (or a new scripts/fleet-cost.sh) loops over the org's repos, runs
   run-report --json in each, and prints one table: project, features in flight, spend
   last 30 days, top rework agent. Keep it stdlib/bash like the existing fleet scripts.
6. Add a paragraph to config/model-routing.yml pointing at the rework metric as the
   evidence standard for re-tiering an agent.

Closing block: run every self-test. Bump the plugin version (minor). Conventional Commits,
linear history. Report the budget defaults you chose and why.
```

---

## 9. Plugin distribution and adapter smoke tests

```
Give the plugin a real distribution and upgrade path, and make the adapter outputs
impossible to ship broken.

Context: the marketplace in .claude-plugin/marketplace.json is a local path, so every
teammate runs whatever commit they last pulled and `claude plugin update` has nothing to
update from. The Copilot and OpenCode adapters (adapters/copilot/generate.py,
adapters/opencode/generate.py) generate their outputs from the Claude plugin; a recent
commit found they had shipped 44 empty files, caught only by hand.

Do this:
1. Read docs/VERSIONING.md, Formula/wellforge.rb, scripts/release-notes.sh,
   commands/release.md, .claude-plugin/marketplace.json, wellforge-plugin/README.md and
   both adapters' README.md and SMOKE-TEST.md.
2. Make the marketplace installable from the git remote: the marketplace.json source
   should reference the plugin by git URL + tag (check the current marketplace format with
   the claude-code-guide agent), the README install section should show the git-based
   install as Option B and keep the local checkout as the contributor path, and
   commands/release.md should tag the plugin series so `claude plugin update` picks it up.
   Do not conflate this with the template `vX.Y.Z` series or `gates-v*`; add the plugin
   series to docs/VERSIONING.md with the same never-tag-two-series-on-one-commit rule.
3. Generated projects pin the plugin: templates write .claude/settings.json (or the
   equivalent the contract allows) with the marketplace and plugin version, and
   /wellforge:upgrade bumps it. Coordinate with the manifest field from the
   plugin-version item if it exists.
4. Adapter smoke test in ci.yml: generate both adapters into a temp dir and assert
   (a) no generated file is empty, (b) every relative link inside generated markdown
   resolves, (c) every plugin command/agent/skill has a generated counterpart or is
   explicitly listed as intentionally-absent in the adapter README, (d) the generated
   model names match config/model-tiers.yml for that tool via scripts/check-routing.py
   --tool. Make SMOKE-TEST.md the human-readable version of the same checks.
5. commands/doctor.md: report the install source (local path vs marketplace tag) and
   whether a newer plugin tag exists.

Closing block: run every self-test. Bump the plugin version (minor). Conventional Commits,
linear history. Report the exact install commands a new teammate runs.
```

---

## 10. Per-worktree databases for parallel implementation

```
Pay the deferred half of the parallel-execution story: a per-worktree database and a
dev-database guard in the JVM and Hono presets, so worktree isolation is true for the
database too.

Context: CLAUDE.md and skills/worktree-isolation/SKILL.md are explicit that a worktree
isolates the checkout, not the database, ports, containers or migration counter, and that
the template half (per-worktree test databases, a dev-database guard) is deferred. Until
it lands, the shared-state preflight forces most backend batches to run sequentially. This
is a TEMPLATE change (templates/spring-kotlin-react, templates/hono-react), so it is its
own vX.Y.Z template release, separate from any plugin bump.

Do this:
1. Read skills/worktree-isolation/SKILL.md fully (shared-state enumeration, env carry-in,
   environment faults), skills/connections/references/environments.md, skills/mise/
   SKILL.md, both presets' compose files, mise.toml files, test configuration
   (Testcontainers on JVM, the Hono testing reference) and templates/_shared/CONTRACT.md.
2. Design first, as an ADR (adr-writer agent): derive a database name and port offset
   from a stable worktree identity (hash of `git rev-parse --show-toplevel`), inject it
   through .mise.local.toml or a mise [env] template so nothing is hard-coded, and decide
   whether integration tests use Testcontainers per worktree (preferred, no shared
   container) while `mise run dev` uses one named compose project per worktree
   (`COMPOSE_PROJECT_NAME`). State the failure shape if two worktrees collide.
3. Implement it in both presets: compose project name and DB name/port from the derived
   identity; Liquibase/Drizzle migration targets follow the same variable; a
   `mise run db:guard` task that refuses to run migrations or destructive test setup
   against a database whose name does not match the current worktree identity, and is
   wired into the test and dev tasks. Keep the copier contract intact (no new required
   answers; document any new optional one in CONTRACT.md).
4. Update worktree-isolation: the database row in the shared-state enumeration moves from
   "sequential unless isolated" to "isolated by the preset from template vX.Y.Z; older
   projects stay sequential", and the preflight checks the template version from
   .forge/manifest.json to decide. Update the environment-fault guidance for the new
   variable.
5. Verify end to end: scaffold both presets with copier --defaults into a temp dir, create
   two worktrees, run `mise run test` in both concurrently, and show both pass with
   distinct databases. Add that to the preset smoke test in ci.yml if runtime allows,
   otherwise document it in the template's SMOKE-TEST.
6. Bump the template_version default, tag the template series only, and add the upgrade
   note so existing projects get it through /wellforge:upgrade.

Closing block: run the preset smoke tests and every plugin self-test. Conventional Commits,
linear history, no plugin version bump unless plugin files changed (then a separate
commit). Report the concurrency test output and any preset where isolation is partial.
```
