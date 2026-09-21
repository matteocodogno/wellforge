# GitHub Copilot adapter

Projects the WellForge workflow onto [GitHub Copilot](https://docs.github.com/copilot) in
**VS Code**. Option (b): the Claude Code plugin (`wellforge-plugin/`) stays the source of
truth; this **generates** Copilot-native files from it, so there's one place to maintain
until the shared core is extracted.

Targets the VS Code Copilot **customization surface** (prompt files, custom chat modes,
instructions, `.vscode/mcp.json`) — richer than the Copilot CLI. Direct parallel of the
[OpenCode adapter](../opencode/README.md).

## Generate

```bash
uv run --with pyyaml python adapters/copilot/generate.py \
  --out <project-dir> --provider anthropic
```

Writes into `<project-dir>`:

| Output | From | Notes |
|---|---|---|
| `.github/prompts/wf-*.prompt.md` | `wellforge-plugin/commands/` | slash commands → prompt files (`/wf-spec`); `mode: agent`; `$ARGUMENTS` → `${input:args}` seeded with the command's `argument-hint` |
| `.github/chatmodes/wf-*.chatmode.md` | `wellforge-plugin/agents/` | each subagent → a custom chat mode (`wf-architect`); routed `model`, `tools` allowlist mapped from the Claude `tools:`/`disallowedTools:` |
| `.github/instructions/wf-*.instructions.md` | path-mappable `skills/` | lean, `applyTo`-scoped pointer that loads only when matching files are in context (e.g. `*.kt` → Spring Boot Kotlin) |
| `.github/wf-skills/<name>/` | `wellforge-plugin/skills/` | the FULL skills (SKILL.md + `references/`), refs translated — the knowledge base, read on demand, never auto-loaded |
| `.github/copilot-instructions.md` | (generated) | thin repo-wide guide: workflow, chat-mode roles, quality floor |
| `.vscode/mcp.json` | `wellforge-plugin/.mcp.json` | `mcpServers` → VS Code's `servers`; merges, doesn't clobber |
| `lefthook.yml` | `adapters/copilot/githooks/` | git-hook enforcement fallback (static) — secret-scan, lint, spec-drift, compile |

All refs are namespaced `wf-` (parity with OpenCode): `/wellforge:x` → `/wf-x`, bare agent
refs → `wf-<agent>` — so nothing clashes with a user's own `/spec` or chat modes.

## Provider / model routing

Models come from `routing(agent → tier) × tiers(copilot → provider → tier → model)` in
`wellforge-plugin/config/`. `--provider anthropic` (default, for parity) | `openai` |
`google`. Copilot resolves the `model:` frontmatter against its **picker display names**,
which change often and vary by plan — treat all of them as templates and confirm the names
your Copilot plan exposes. The tier *assignment* is shared with Claude Code; only the
concrete name differs.

## Support tier (honest)

This reaches the **workflow + agents + skills + MCP** — the bulk of WellForge — via VS Code's
customization surface. Two things do NOT port cleanly, and the adapter says so:

**1. No hook runtime.** Copilot has no PreToolUse/PostToolUse/Stop equivalent. The high-value
LOCAL hooks are ported to git hooks (`lefthook.yml`); the DURABLE enforcement stays the CI
quality gates (`.github/workflows/`).

| Claude Code hook | Copilot port | Ported |
|---|---|---|
| pre-bash-guard | `lefthook` pre-commit secret-scan (`.env`/`.pem`/`.key`/`secrets.yml`) | ✓ (the security floor; the destructive-shell-command blocks have no commit-time analog) |
| post-lint | `lefthook` pre-commit lint-ts / lint-kotlin (prettier/eslint/ktlint, `stage_fixed`) | ✓ |
| stop-verify (spec-drift) | `lefthook` pre-commit spec-drift | ✓ blocks on drift |
| stop-verify (compile) | `lefthook` pre-push typecheck-ts / compile-kotlin | ✓ |
| post-spec-guard (lifecycle gates) | — | ✗ no PostToolUse event. The `status: done` gate and the raise-only `rigor:` rule are **prompt promises here**, not mechanism: `/wf-done` still evaluates the gate, but nothing stops a hand-edit of the frontmatter. The CI gates remain the durable half |
| pre-file-guard (secret files) | `lefthook` pre-commit secret-scan | ~ partial. The commit-time scan catches a secret file being COMMITTED; it cannot stop Copilot READING one into the chat transcript, which is the half with no analog |
| notify | — | ✗ no event, and nothing to notify — Copilot has no long-running background session to be told about |
| trace-subagent (token observability) | — | ✗ no Copilot event — covered by **CI gates** |
| session-start / pre-compact | — | ✗ (lower value) |

**2. No parallel multi-agent orchestration.** Copilot runs ONE chat mode at a time and can't
spawn/parallelise subagents. `/wf-orchestrate` and `/wf-implement` degrade to a single-session
"wear each hat in sequence" flow (the user switches chat modes as the pipeline progresses);
Copilot's cloud coding agent is the closest autonomous path. Pillars 2–3 lose execution
fidelity here — the structure, specs, conventions, gates, and eval are fully portable.


## Coverage (machine-checked)

`adapters/smoke-test.py` asserts every plugin command, agent and skill has a counterpart
here. A deliberate gap is legitimate — an **undeclared** one is the bug, so the exceptions
live in this block and nowhere else. Empty lists below mean full parity today.

```yaml wellforge-adapter-coverage
intentionally_absent:
  commands: []
  agents: []
  skills: []
```

Hooks are the exception this block does not cover: they have no counterpart artifact to
count, so the per-hook table above is their record. See [`SMOKE-TEST.md`](SMOKE-TEST.md)
for the human pass this script is the mechanical half of.

## Status

Generator complete: **20 prompts · 10 chat modes · 9 scoped instructions + the full skill
library (21 skills, refs translated) · 4 MCP servers · git-hook enforcement fallback.**
Provider swap working; all generated frontmatter validated as YAML; ref translation clean
(0 leftover `/wellforge:`).

Those counts are not maintained by hand any more, and they were wrong (17 / 13 / 3) before
`adapters/smoke-test.py` existed — which is the whole argument for it. CI now regenerates
this adapter on every push and asserts the output is non-empty, that its links resolve,
that coverage is complete, and that its model names match `config/model-tiers.yml`.

Next: `wellforge install --tool copilot` wiring to lay this down automatically. The manual
VS Code pass ([`SMOKE-TEST.md`](SMOKE-TEST.md)) stays the check for what no script can see —
whether Copilot actually loads and honours these files.
