# OpenCode adapter

Projects the WellForge workflow onto [OpenCode](https://opencode.ai). Option (b): the
Claude Code plugin (`wellforge-plugin/`) stays the source of truth; this **generates**
OpenCode-native files from it, so there's one place to maintain until the shared core is
extracted.

## Generate

```bash
uv run --with pyyaml python adapters/opencode/generate.py \
  --out <project-dir> --provider anthropic
```

Writes into `<project-dir>`:

| Output | From | Notes |
|---|---|---|
| `.opencode/agents/wf-*.md` | `wellforge-plugin/agents/` | `wf-` prefixed (`wf-architect`); `mode: subagent`, `model` (provider/model), `permission` block from the Claude `tools:` list |
| `.opencode/commands/wf-*.md` | `wellforge-plugin/commands/` | `$ARGUMENTS` identical; **`wf-` prefixed** (`/wf-spec`) — OpenCode commands are unnamespaced, so the prefix avoids clashing with a user's existing `/spec` etc. `/wellforge:x` → `/wf-x`, bare agent refs → `wf-<agent>` |
| `.opencode/skills/` | `wellforge-plugin/skills/` | SKILL.md is cross-tool — copied, refs translated |
| `opencode.json` (`mcp`) | `wellforge-plugin/.mcp.json` | translated to OpenCode's `mcp` schema (local/remote) |
| `.opencode/plugins/wellforge.js` | `adapters/opencode/plugin/` | enforcement plugin (static) — bash guard, post-lint, spec-drift |

## Provider / model routing

Models come from `routing(agent → tier) × tiers(opencode → provider → tier → model)` in
`wellforge-plugin/config/`. `--provider anthropic` (default, verified) | `openai` | `google`
(templates — verify the model ids for your account). The tier *assignment* is shared with
Claude Code; only the concrete model differs.

## Support tier (honest)

This reaches the **workflow + agents + skills + MCP + enforcement** — the bulk of WellForge.
The enforcement plugin (`.opencode/plugins/wellforge.js`) ports the high-value hooks:

| Claude Code hook | OpenCode event | Ported |
|---|---|---|
| pre-bash-guard | `tool.execute.before` (throw = deny) | ✓ (guard regexes parity-tested 13/13) |
| post-lint | `file.edited` | ✓ prettier/eslint/ktlint, best-effort |
| stop-verify (spec-drift) | `session.idle` | ✓ warns (can't block on idle) |
| trace-subagent (token observability) | — | ✗ no OpenCode subagent-usage event |
| session-start / pre-compact | `session.created` / `experimental.session.compacting` | not yet (lower value) |

Remaining gaps vs. Claude Code, honestly:
- **Token-trace observability** has no OpenCode equivalent event — covered by **CI gates**.
- **Orchestration** uses OpenCode subagents (`@agent` / task); parallel-dispatch fidelity
  depends on OpenCode's runtime.

## Status

Validated: 10 agents · 10 commands · skills · 3 MCP servers · enforcement plugin (valid
ESM, guard parity 13/13), provider swap working. Next: `wellforge setup/migrate` wiring
(tool + provider choice) to lay this down automatically.
