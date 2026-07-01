# Multi-tool support — strategy (OpenCode · Codex · Copilot CLI · Claude Code)

WellForge is Claude Code-native today. Colleagues use OpenCode, Codex CLI, and Copilot
CLI. This is the research-backed plan to support them — what's portable, what isn't, and
how, with honest support tiers. **Status: proposal — needs a scope decision before build.**

## What actually changed in the ecosystem (the good news)

A de-facto cross-tool standard has converged. As of mid-2026, **all four** tools support:

| Capability | Claude Code | OpenCode | Codex CLI | Copilot CLI |
|---|---|---|---|---|
| **AGENTS.md** (context/instructions) | ✓ (via import) | ✓ native | ✓ native | ✓ native |
| **SKILL.md skills** (progressive disclosure) | ✓ | ✓ | ✓ (prompts deprecated → skills) | ✓ (`.github/skills`, `.claude/skills`, `.agents/skills`) |
| **MCP servers** | ✓ | ✓ | ✓ | ✓ (GitHub MCP preconfigured) |
| **Slash commands / prompts** | ✓ `/x` | ✓ `.opencode/commands` | ✓ `~/.codex/prompts` (deprecated) | ✓ `/x` |
| **Subagents / parallel dispatch** | ✓ Task tool | ✓ subagents | ~ limited | ~ agent modes/subagents |
| **Lifecycle hooks** | ✓ rich (7) | ✓ TS plugins | ✗ minimal | ✗ minimal |

**WellForge already speaks the universal three** (AGENTS.md + skills + MCP). That's most of
the value. The gap is the *premium* layer: multi-agent orchestration and enforcement hooks.

## What this means for each pillar

| WellForge pillar | Portability |
|---|---|
| 4 Scaffolder · 5 Gates · 6 Lifecycle | **Already tool-neutral** (Copier, GitHub Actions, AGENTS.md). No work. |
| 1 Spec-driven workflow | **Portable** — it's conventions (the `spec-driven` skill) + commands. Skill ports as-is; commands re-expressed per tool. |
| 2 Agent team | **Partially portable** — the 10 agent definitions become *skills the agent adopts* on tools without subagents; *dispatched subagents* where supported. |
| 3 Orchestrator | **Degrades by tool** — parallel multi-agent dispatch only on Claude Code/OpenCode; on Codex/Copilot it's a *documented sequential procedure* the single agent follows. |
| Eval (P1) | **Portable** — rubric is a config file; the LM-judge is a skill/role + the headless `run-eval.py` (already tool-agnostic, calls the API directly). |
| Observability (P2) | **Hook-dependent** — run traces need a SubagentStop-equivalent; the commands can still write traces explicitly, but auto token capture is Claude Code/OpenCode-only. |
| Model routing (P3) | **Tool-specific** — each tool selects models differently; the *policy* (config) is shared, the *mechanism* per tool. |
| Hooks (guard/drift/lint) | **Claude Code-rich; OpenCode via plugins; Codex/Copilot minimal** — degrade to CI-gate enforcement (which is universal). |

## Proposed architecture — tool-neutral core + thin adapters

Define the workflow **once**, emit each tool's native packaging. Do NOT fork 4 copies.

```
wellforge-core/                      ← tool-neutral source of truth
  skills/        spec-driven, rigor-tiers, connections, stack skills, observability, rubric (SKILL.md — already cross-tool)
  agents/        the 9 role prompts (plain markdown — consumed as subagents OR adopted as role-skills)
  workflow/      the spec→plan→tasks→implement→eval procedure as prose (drives tools without commands)
  AGENTS.md      the canonical context block

adapters/
  claude-code/   the existing plugin (richest: subagents, 7 hooks, commands, MCP)   ← exists
  opencode/      generate .opencode/{agents,commands,skills}/ + plugin for hooks      ← near 1:1
  codex/         ~/.codex/skills + AGENTS.md + prompt files + config.toml MCP         ← workflow + skills
  copilot/       .agents/skills (or .github/skills) + AGENTS.md + mcp-config.json     ← workflow + skills
```

`wellforge setup` (or a new `wellforge install --tool <name>`) lays down the right adapter
for the user's tool. The CLI already manages env per tool.

## Honest support tiers

Don't pretend every tool gets the full experience — set expectations.

- **Tier 1 — Claude Code (full):** commands, parallel 10-agent orchestration, 7 hooks
  (guard/drift/lint/observability), eval gate, run traces. The reference implementation.
- **Tier 1 — OpenCode (near-full):** native agents + commands + skills; hooks via a TS
  plugin. Realistically reaches ~90% — the closest port, and your colleagues use it.
- **Tier 2 — Codex / Copilot CLI (workflow + skills):** the full spec-driven discipline,
  role skills, rubric, MCP connections, and CI gates — but the orchestrator runs as a
  *sequential* procedure (single agent adopting roles in turn), not parallel dispatch, and
  enforcement leans on **CI gates** (universal) rather than local hooks. Still the bulk of
  the value: structure, specs, conventions, gates, eval.

The honest line: **what makes WellForge valuable — the spec-driven structure, the quality
gates, the eval, the conventions — is fully portable. What's Claude Code-premium is the
parallel multi-agent *execution*, and that gap is covered by sequential role-adoption +
CI enforcement on the lighter tools.**

## Phased plan

1. **Extract the tool-neutral core** (refactor, no behavior change): pull the conventions,
   role prompts, rubric, and workflow procedure into a `wellforge-core/` shared source the
   Claude Code plugin also consumes. Proves nothing forks.
2. **OpenCode adapter** (highest ROI — closest model, colleagues use it): generate
   `.opencode/` from core; port hooks to an OpenCode plugin. Validate the adapter model.
3. **Codex + Copilot adapters** (Tier 2): AGENTS.md + skills + MCP config + the sequential
   workflow procedure; lean on CI gates for enforcement. Document the degraded orchestration.
4. **`wellforge install --tool <name>`**: one command lays down the right adapter; `doctor`
   detects the tool and checks its wiring.

## Decisions needed before building

1. **Scope/priority:** all three now, or OpenCode first (prove the model) then Codex/Copilot?
   Recommendation: **OpenCode first** — it validates the core+adapter split with the least
   friction and the most colleague usage.
2. **Acceptable degradation:** is "Tier 2 = sequential workflow + CI enforcement, no
   parallel agents/local hooks" acceptable for Codex/Copilot, or is parallel orchestration
   a hard requirement (which would rule those tools out for the full experience)?
3. **Maintenance appetite:** four adapters is real ongoing cost (the "max 2 presets"
   discipline applies — every tool API churn is N× work). Worth committing to all four, or
   support Claude Code + OpenCode well and treat Codex/Copilot as "AGENTS.md + skills +
   gates, BYO-driving"?

## Bottom line

This is very buildable — far more than it would have been a year ago, because skills +
AGENTS.md + MCP converged into a real standard WellForge already uses. The core+adapter
architecture avoids forking. The realistic first deliverable is the **core extraction +
OpenCode adapter**; Codex/Copilot follow as Tier 2. The decisions above set the scope.
