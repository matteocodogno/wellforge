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
| `.opencode/agents/*.md` | `wellforge-plugin/agents/` | OpenCode frontmatter: `mode: subagent`, `model` (provider/model), `permission` block mapped from the Claude `tools:` list |
| `.opencode/commands/*.md` | `wellforge-plugin/commands/` | `description` + body; `$ARGUMENTS` works identically; `/wellforge:x` → `/x` (OpenCode commands are unnamespaced) |
| `.opencode/skills/` | `wellforge-plugin/skills/` | SKILL.md is cross-tool — copied, refs translated |
| `opencode.json` (`mcp`) | `wellforge-plugin/.mcp.json` | translated to OpenCode's `mcp` schema (local/remote) |

## Provider / model routing

Models come from `routing(agent → tier) × tiers(opencode → provider → tier → model)` in
`wellforge-plugin/config/`. `--provider anthropic` (default, verified) | `openai` | `google`
(templates — verify the model ids for your account). The tier *assignment* is shared with
Claude Code; only the concrete model differs.

## Support tier (honest)

This reaches the **workflow + agents + skills + MCP** — the bulk of WellForge. Two gaps
vs. Claude Code, by design for now:

- **Hooks** (pre-bash guard, spec-drift, post-lint, observability traces) are **not**
  generated — OpenCode hooks are TypeScript plugins (a follow-up). Until then, enforcement
  on OpenCode leans on the **CI quality gates** (universal) rather than local hooks.
- **Orchestration** uses OpenCode subagents (`@agent` / task); parallel dispatch fidelity
  depends on OpenCode's runtime.

## Status

Generator validated: 10 agents · 10 commands · skills · 3 MCP servers, all frontmatter
valid, provider swap working. Next: hooks-as-TS-plugin, and `wellforge setup/migrate`
wiring (tool + provider choice) to lay this down automatically.
