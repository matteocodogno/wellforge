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
| post-spec-guard (lifecycle gates) | — | ✗ OpenCode has no post-edit event that can refuse. The `status: done` gate and the raise-only `rigor:` rule are **prompt promises here**, not mechanism; the CI gates remain the durable half |
| pre-file-guard (secret files) | `tool.execute.before` | ~ partial. The plugin's guard inspects BASH command text, so it covers `cat .env`; a direct Read of a secret file does not pass through that event and is not blocked |
| notify | — | ✗ no equivalent event |
| trace-subagent (token observability) | — | ✗ no OpenCode subagent-usage event |
| session-start / pre-compact | `session.created` / `experimental.session.compacting` | not yet (lower value) |

Remaining gaps vs. Claude Code, honestly:
- **Token-trace observability** has no OpenCode equivalent event — covered by **CI gates**.
- **Orchestration** uses OpenCode subagents (`@agent` / task); parallel-dispatch fidelity
  depends on OpenCode's runtime.


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

Validated: **10 agents · 20 commands · 21 skills · 4 MCP servers · enforcement plugin**
(valid ESM, guard parity 13/13), provider swap working.

CI regenerates this adapter on every push and asserts four things about the output —
non-empty files, resolving links, complete coverage, and model names matching
`config/model-tiers.yml` (`adapters/smoke-test.py`). The counts above came from that run,
not from memory; the Copilot adapter's equivalent line had drifted by 3 commands and 8
skills before the check existed.

Next: `wellforge setup/migrate` wiring (tool + provider choice) to lay this down
automatically, and the manual OpenCode pass in [`SMOKE-TEST.md`](SMOKE-TEST.md) for what a
script cannot see — whether OpenCode loads and honours these files.
