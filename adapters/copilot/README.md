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
| trace-subagent (token observability) | — | ✗ no Copilot event — covered by **CI gates** |
| session-start / pre-compact | — | ✗ (lower value) |

**2. No parallel multi-agent orchestration.** Copilot runs ONE chat mode at a time and can't
spawn/parallelise subagents. `/wf-orchestrate` and `/wf-implement` degrade to a single-session
"wear each hat in sequence" flow (the user switches chat modes as the pipeline progresses);
Copilot's cloud coding agent is the closest autonomous path. Pillars 2–3 lose execution
fidelity here — the structure, specs, conventions, gates, and eval are fully portable.

## Status

Generator complete: 17 prompts · 10 chat modes · 9 scoped instructions + skill library (13
skills, refs translated) · 3 MCP servers · git-hook enforcement fallback. Provider swap
working; all generated frontmatter validated as YAML; ref translation clean (0 leftover
`/wellforge:`). Next: manual VS Code smoke test (prompts / chat modes / MCP load), then
`wellforge install --tool copilot` wiring to lay this down automatically.
</content>
