# WellForge Claude Code Plugin

Full-stack development plugin for Spring Boot Kotlin + React TypeScript monorepos.

## Install

### For a teammate — from the git marketplace (the normal path)

Nothing to clone. The **wellforge repo root** is a plugin marketplace
(`.claude-plugin/marketplace.json`), and its entry points at a `git-subdir` source pinned to
a `plugin-v*` tag — so what you install is a named release, not whatever `main` happened to
be that morning.

```bash
claude plugin marketplace add matteocodogno/wellforge
claude plugin install wellforge@wellforge --scope user
```

(or interactively: `/plugin` → `wellforge` → install → scope: user)

Later, to move to a newer release:

```bash
claude plugin marketplace update wellforge   # re-read the manifest (it names the new tag)
claude plugin update wellforge@wellforge
```

> **What "update" resolves to is not documented.** The manifest pins a tag and Claude Code
> records the installed `version` + `gitCommitSha` in
> `~/.claude/plugins/installed_plugins.json`, but whether `plugin update` follows the tag in
> the refreshed manifest, the default branch, or the `version` field is not stated in the
> plugin-marketplace docs. Treat the pair of commands above as the reliable sequence, and
> check the recorded version afterwards:
> `jq -r '.plugins["wellforge@wellforge"][0].version' ~/.claude/plugins/installed_plugins.json`.
> `/wellforge:doctor` reports it for you, alongside where the plugin came from.

### For a contributor — from your own checkout

Marketplace installs deliberately fetch the tagged release from git, so a local clone
registered as a marketplace still gives you the *published* plugin, not your edits. To run
the code you are editing, bypass the marketplace:

```bash
claude --plugin-dir <wellforge-checkout>/wellforge-plugin
```

That is per-launch and affects nothing else — which is what you want while iterating, since
an in-place edit to an installed plugin is cached by version and would not take effect
anyway until the version is bumped.

### Verify

Inside Claude Code:
```
/plugin              → wellforge listed under Installed
/mcp                 → sequential-thinking, playwright, github, context-hub connected
/hooks               → 7 hooks listed
/wellforge:doctor    → full health report, install source, and the command index
```

---

## Structure

| Path | What |
|---|---|
| `.mcp.json` | sequential-thinking, playwright, github, context-hub MCP servers |
| `commands/spec.md` | `/wellforge:spec` — interview → feature spec (step 1 of 3) |
| `commands/plan.md` | `/wellforge:plan` — approved spec → technical plan (step 2 of 3) |
| `commands/design.md` | `/wellforge:design` — UX flows, screens & states, component reuse, a11y (UI features) |
| `commands/tasks.md` | `/wellforge:tasks` — approved plan → dependency-aware task list (step 3 of 3) |
| `commands/implement.md` | `/wellforge:implement` — implement chosen tasks (IDs/range/next/all), parallel by DAG, QE-verified |
| `commands/orchestrate.md` | `/wellforge:orchestrate` — full team pipeline: classify → spec → plan → tasks → parallel devs → QE verdict, 2 human gates |
| `commands/eval.md` | `/wellforge:eval` — LM-judge scores the feature against the central rubric (gate into `done`) |
| `commands/done.md` | `/wellforge:done` — verify the tier-aware done gate, then record `status: done` (or retire as superseded) |
| `commands/doctor.md` | `/wellforge:doctor` — health check (tools, MCP, hooks, guards, `--tests`) + the command index |
| `commands/status.md` | `/wellforge:status` — recap every feature's phase + the next command to run (read-only) |
| `commands/triage.md` | `/wellforge:triage` — spec-health heartbeat: stale in-progress, unresolved drift, passed-QE-never-eval'd (read-only digest) |
| `commands/new.md` | `/wellforge:new` — interview → stack recommendation → Copier scaffold → build verify → connections |
| `commands/upgrade.md` | `/wellforge:upgrade` — copier update to a newer template version + AI conflict resolution + gates |
| `commands/adopt.md` | `/wellforge:adopt` — brownfield onboarding: AI-readiness, spec workflow, gates with measured baseline |
| `commands/extract-template.md` | `/wellforge:extract-template` — profile a project's stack, gap-check it, optionally extract an org-internal Copier template |
| `commands/spike.md` | `/wellforge:spike` — main-loop build from a one-paragraph brief, advisory gates, no agents (rigor: spike) |
| `commands/promote.md` | `/wellforge:promote` — graduate a feature (or the project) up a rigor tier, paying the deferred debt |
| `commands/release.md` | `/wellforge:release` — version bump + CHANGELOG from Conventional Commits, tag, GitHub release |
| `commands/terse.md` | `/wellforge:terse` — toggle terse conversational output for this run |
| `commands/terse-compress.md` | `/wellforge:terse-compress` — one-way compression of a WellForge-owned file, behind a fact-preservation gate |
| `agents/product-owner.md` | PO — spec.md: problem, user stories, ACs, non-goals |
| `agents/architect.md` | Architect — plan.md: architecture, contracts, AC→test mapping |
| `agents/designer.md` | Designer — design.md: flows, screens, component reuse, a11y |
| `agents/frontend-dev.md` | FE dev — implements tasks per react-ts-vite conventions |
| `agents/backend-dev.md` | BE dev — implements tasks per stack skill conventions |
| `agents/devops.md` | DevOps — CI/CD, infra, tool connections (verified, not assumed) |
| `agents/quality-engineer.md` | QE — AC verification, gates run, evidence-based verdict (deterministic half) |
| `agents/evaluator.md` | Evaluator — LM-judge, rubric-scored verdict (non-deterministic half) |
| `agents/owasp-reviewer.md` | Specialist: OWASP Top 10 security review |
| `agents/adr-writer.md` | Specialist: Architecture Decision Record writer |
| `hooks/hooks.json` | 7 lifecycle hooks |
| `hooks/scripts/session-start.sh` | Injects git state + domain glossary at session start |
| `hooks/scripts/pre-bash-guard.sh` | Blocks recursive deletion from root/home, SQL nukes, pipe-to-shell, force push / `reset --hard` / force branch delete, and commands naming a secret file |
| `hooks/scripts/pre-file-guard.sh` | The same protected files for the Read/Write/Edit/Grep tools — it reads the path parameter, so no text guessing |
| `hooks/scripts/post-lint.sh` | ts/tsx → Prettier+ESLint · kt/kts → ktlintFormat |
| `hooks/scripts/post-spec-guard.sh` | **The lifecycle rules, mechanically.** On any edit to `specs/*/spec.md`\|`brief.md`: `status: done` only when `forge-state.py`'s `done_gate.passes`, `rigor:` never downward, no reopening a closed feature by edit, no status outside the enum. PostToolUse, so it detects and demands a revert rather than preventing — see the note below |
| `hooks/scripts/notify.sh` | macOS notification + Telegram DM |
| `hooks/scripts/stop-verify.sh` | Blocks on spec drift + type/compile errors before Claude stops — over the branch's whole change set (merge base ∪ working tree), not just unstaged files. **Surprise to know about:** a cosmetic `spec.md` edit committed earlier on the branch blocks *every* Stop until `/wellforge:tasks` re-syncs (which stamps `synced:` even when nothing else changes). That is the drift rule working; it does not feel like it. |
| `hooks/scripts/pre-compact-backup.sh` | Snapshots session state before compaction |
| `hooks/scripts/trace-subagent.sh` | SubagentStop → best-effort token events to `.forge/runs/.events.jsonl` (observability) |
| `scripts/forge-state.py` | **Feature lifecycle state, deterministically** — walks `specs/`, validates frontmatter against the schema, counts tasks, computes drift from git order, joins QE/eval verdicts, resolves the tier, evaluates the done gate. `--json` emits `forge-state/v1`; status, triage, done and promote all read it instead of re-deriving |
| `config/spec-frontmatter.schema.json` | Machine-readable mirror of the spec-driven skill's frontmatter; `check-docs.py` fails if its enums drift from the skill |
| `scripts/run-report.py` | Summarizes `.forge/runs/` — agents, verdicts, drift, estimated cost; `--budget` (spend vs tier ceiling, top consumer) and `--rework` (QE/security fail rounds per feature and agent — the re-tiering evidence) |
| `scripts/check-routing.py` | Verifies agent frontmatter models match the routing policy (drift guard) |
| `scripts/check-budget.py` | Measures what the plugin injects into **every** session (all skill/command/agent descriptions) and fails when it exceeds the ratchet in `config/budget.yml` |
| `config/budget.yml` | The session-injection ceiling, and why it moves only by decision |
| `config/security-triggers.yml` | Path globs + substrings whose presence in a batch dispatches the owasp-reviewer; `always_at_tier: [production]` |
| `config/rigor-budgets.yml` | Advisory per-tier cost/wall-clock ceilings + the rework thresholds — surfaced by triage, never blocking |
| `scripts/security-triggers.py` | Evaluates those triggers against `touch:` ∪ `git diff` — what implement/orchestrate call before QE |
| `docs/PLUGIN-MIGRATIONS.md` (repo) | Project-side changes per plugin minor — read by `/wellforge:upgrade`, reported by `/wellforge:doctor` |
| `config/model-pricing.yml` | Per-model price table for run-report cost estimates |

### What the guards can and cannot do

Two hooks protect secrets and destructive operations, and they work differently on purpose:

- **`pre-file-guard.sh`** reads the tool's path **parameter** (Read/Write/Edit/MultiEdit/
  NotebookEdit, and Grep — which sends `path` and, in content mode, prints matching lines).
  It is exact about the file it is given: a path is protected or it isn't.
- **The two guards must agree.** They protect the same files by different means, so a file
  one blocks and the other waves through is a hole, not a nuance — `Read` of
  `.mise.local.toml` was blocked while `cat` sailed past until 2026-09-20. The asymmetry
  that IS deliberate: `.mise.local.toml` is read-denied and **write-allowed** in both, because
  it is the sanctioned secret store the setup flow creates. Metadata-only commands
  (`ls`, `stat`, `test`, `git check-ignore`) may name a protected file — they reveal nothing,
  and refusing them is what taught people to route around the guard. That carve-out applies
  only to a **single simple command**: a separator (`&&`, `;`, `|`, `$(…)`) disqualifies it,
  because `ls . && cat <secret>` starts with `ls`.
- **Enumerate the small set, not the unbounded one.** The `.mise.local.toml` rule is
  inverted for this reason: it denies *any* command naming the file except a handful of
  sanctioned write shapes (`>`/`>>` into it, `tee`, `touch`, `mise set`). The first version
  allow-listed readers — `cat`, `head`, `less` — and `grep`, `awk`, `sed`, `cp`,
  `python3 -c`, `curl -d @file` and `git diff` all walked straight through. There is no
  finite list of ways to read a file; there is a finite list of ways you are meant to write
  one.
- **`pre-bash-guard.sh`** can only match the **text of a command**, because that is all a
  shell invocation gives it. Two consequences worth knowing before you file a bug:
  1. **False positives.** A command that merely *mentions* a protected name is blocked even
     if it opens nothing — `grep -rn ".env" docs/`, a loop containing the string, this very
     README's examples. That is the accepted cost of a text-only rule; `.env.example`,
     `*.jinja` and `--force-with-lease` are scrubbed because they came up constantly, and
     more exceptions get added the same way. Work around it by not naming the file, or run
     the command yourself.
  2. **A directory-wide content grep is not coverable.** `Grep` *at* a protected file is
     blocked; `Grep` at a directory whose pattern happens to match a line inside one is not,
     because no path check can see that. Same for `cat dir/*`. If a secret must never reach
     a transcript, the file being unreadable is the guarantee — the guard is not.
  3. **It is a seatbelt, not a sandbox.** Text matching is evadable by anyone trying —
     variable indirection, base64, an unusual spelling. It is there to stop an accident, not
     an adversary. Real enforcement lives where it cannot be talked around: the gitleaks
     pre-commit hook, the security-floor CI gate, and branch protection.

Both have regression matrices (`hooks/scripts/tests/`, run by CI). Every case in them is
something a guard once got wrong — add yours there rather than only widening a regex.

| `config/model-routing.yml` | Tool-neutral: agent → tier (frontier/mid/cheap) — the portable routing policy |
| `config/model-tiers.yml` | Per-tool: tier → concrete model (claude aliases, opencode provider/model) |
| `skills/connections/` | Standardized tool-connection checklists (GitHub, MCP, environments) — each ends with a verification command |
| `skills/frontend-design/` | visual direction for NEW product surfaces — the surface-class gate and two-pass token system |
| `skills/git-policy/` | Linear history + Conventional Commits — the format, the four enforcement layers, what to do when a gate rejects you |
| `skills/quality-gates/` | What CI enforces, where thresholds live, and the rule that they change only by PR to `gates/` |
| `skills/template-contract/` | The binding contract every Copier template satisfies — one root copier.yml, the shared questions, the manifest, the two version series |
| `skills/heartbeat/` | Scheduled-automation conventions — surface-never-ship, dedup, deterministic-vs-agentic, cost bound |
| `skills/hono-ts-backend/` | Hono + TypeScript + Drizzle + Effect — best practices and scaffolding |
| `skills/kotlin-springboot/` | Spring Boot + Kotlin + jOOQ + Liquibase + Modulith |
| `skills/mise/` | dev-tool version manager — tools, tasks, and the monorepo addressing rule |
| `skills/observability/` | Run-trace (`.forge/runs/`) format conventions — producers and consumers |
| `skills/pulumi-gcp-ts/` | Pulumi IaC in TypeScript on GCP — stacks, ComponentResources, CrossGuard, mock tests |
| `skills/react-ts-vite/` | React + TypeScript + Vite + Mantine + TanStack |
| `skills/rigor-tiers/` | spike / mvp / production — how much pipeline runs, the security floor, the effort cue |
| `skills/self-critique/` | the one bounded pass over your own artifact before the gate that follows |
| `skills/spec-driven/` | Spec-driven workflow conventions (format, status lifecycle, drift rule) |
| `skills/springboot-scaffold/` | JVM routing + module conventions — which generator applies, and how to add a service to an existing monorepo by hand |
| `skills/systematic-debugging/` | root cause before the fix, the 3-attempt architecture stop, never silence a symptom |
| `skills/template-extraction/` | stack profile, preset gap-check, org-internal template extraction with an IP/secret scrub |
| `skills/terse/` | token-efficient conversational output — byte-identical invariant, artifact exemption |
| `skills/visual-companion/` | browser tool the designer uses to show mockups instead of describing them (opt-in, interactive only) |
| `skills/worktree-isolation/` | what a worktree does and does NOT isolate; the shared-state preflight and integration protocol |

## MCP servers

| Server | Transport | Auth |
|---|---|---|
| `sequential-thinking` | stdio | none |
| `playwright` | stdio | none |
| `github` | HTTP | OAuth via `/mcp` on first use |
| `context-hub` | stdio | none |

`telegram` is managed by `telegram@claude-plugins-official` — install separately via `/plugin`.

## Telegram notifications setup

Guided wizard (creates the bot with you, detects your chat id, sends a test message):

```bash
wellforge telegram
```

Config lands in `~/.config/wellforge/telegram.env` (chmod 600, sourced from `~/.zshrc`;
the notify hook also reads it directly). Manual alternative: export
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` yourself — **never commit them**.

## Settings to merge manually

See `settings-snippet.jsonc` — copy into `~/.claude/settings.json`:
```json
{
  "enabledPlugins": {
    "pyright-lsp@claude-plugins-official": true,
    "telegram@claude-plugins-official": true
  },
  "skipDangerousModePermissionPrompt": true,
  "attribution": { "commit": "", "pr": "" }
}
```

> `skipDangerousModePermissionPrompt` — personal machines only, never commit to shared repos.

## Domain glossary (optional)

Create `.claude/context/glossary.md` in your project — injected into every session:
```markdown
# Domain glossary
- **<term>**: <one-line definition the AI should know for this project>
- **<acronym>**: <what it expands to and means in your domain>
```
