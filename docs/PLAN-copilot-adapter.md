# WellForge — GitHub Copilot adapter

Status legend: ☐ todo · ◐ in progress · ☑ done

A plan to let a team run the WellForge workflow inside **GitHub Copilot** (VS Code), for a
customer who uses Copilot as their AI coding tool. WellForge's source of truth is the Claude
Code plugin (`wellforge-plugin/`); this adapter **projects** that plugin onto Copilot's
customization surface — it does not fork or hand-maintain a second copy.

## Precedent (locked)

`adapters/opencode/generate.py` already retargets the plugin onto OpenCode — "Option b: the
Claude Code plugin stays the source of truth; this generates tool-native files from it."
`config/model-tiers.yml` already models multiple tools (`claude`, `opencode`). **The Copilot
adapter is the direct parallel:** a new `adapters/copilot/generate.py` that reads the plugin
and emits Copilot-native artifacts, plus a `copilot:` entry in `model-tiers.yml`.

- **Generate, don't fork.** One place to maintain until a shared core is extracted.
- **`wf-` prefix throughout** (parity with OpenCode): `/wf-spec`, chat mode `wf-architect` —
  avoids clashing with a user's own `/spec` or modes.
- **Reuse the OpenCode generator's proven pieces** — `split_frontmatter`, `translate` (with a
  Copilot variant), and the `routing × tiers` model resolution. Only the *emit* stage is new.

## Artifact mapping

Copilot's surface (`.github/` + `.vscode/`) differs from OpenCode's `.opencode/`, so the emit
stage is new even though the read/translate stage is reused.

| Claude Code plugin | Copilot artifact | Path | Fidelity |
|---|---|---|---|
| `commands/*.md` (slash) | prompt files | `.github/prompts/wf-*.prompt.md` | **High** — `$ARGUMENTS`→`${input:args}`; frontmatter `mode: agent`, `description`, `model` |
| `agents/*.md` (subagents) | custom chat modes | `.github/chatmodes/wf-*.chatmode.md` | **Medium** — persona + `tools` set + `model`; no programmatic subagent spawning |
| stack `skills/*/SKILL.md` | path-scoped instructions | `.github/instructions/wf-*.instructions.md` (`applyTo:` glob) | **Medium** — auto-applied by file glob, no on-demand progressive loading |
| workflow skills (spec-driven, rigor-tiers) | thin repo instructions + inlined into prompts | `.github/copilot-instructions.md` + prompt bodies | **Medium** — can't glob-scope; inline into the prompts that need them to avoid always-on bloat |
| `.mcp.json` | MCP config | `.vscode/mcp.json` | **High** — near-identical schema |
| `config/model-{routing,tiers}` | per-mode `model:` frontmatter | (in each chatmode/prompt) | **Medium** — Copilot models are subscription/picker-driven |
| **hooks** (pre-bash-guard, post-lint, stop-verify, trace) | **no runtime hook API** | git hooks + CI | **Low — main gap** |
| **orchestrate / parallel worktree implement** | single-agent (cloud coding agent) or sequential | — | **Low — main gap** |

## The two honest gaps (and the fallback)

Declared plainly, the way the OpenCode README declares its own gaps — not papered over.

1. **No hook runtime.** OpenCode could port hooks into `.opencode/plugins/wellforge.js`;
   Copilot has no equivalent. Enforcement degrades to two layers we already own:
   - **CI gates** (`.github/workflows/quality-*.yml`) — the durable enforcement, unchanged.
   - **Local git hooks** via a generated `lefthook.yml`: port `pre-bash-guard`→pre-commit
     secret/danger scan, `post-lint`→pre-commit lint, `stop-verify` spec-drift→pre-push warn.
   - **Dropped:** `trace-subagent` token observability (no Copilot event) — same gap OpenCode
     declared, covered by CI.

2. **No multi-agent orchestration.** Copilot can't fan out parallel worktree-isolated dev
   agents. `/wf-orchestrate` degrades to a single-session "wear each hat in sequence" chat
   mode; Copilot's cloud coding agent is the closest autonomous path. Pillars 2–3 lose
   fidelity here — the README says so.

## Skills without progressive disclosure

Copilot instructions are **always-on by glob**, not model-invoked on demand, so we can't dump
13 large skills into context.

- **Stack skills** (`react-ts-vite`, `kotlin-springboot`, `hono-ts-backend`, `pulumi-gcp-ts`,
  …) → `.instructions.md` with an `applyTo:` glob matching that stack's files (e.g.
  `**/*.tsx`). Only load when the user edits relevant files.
- **Workflow skills** (`spec-driven`, `rigor-tiers`) can't be glob-scoped to a file type.
  Keep `copilot-instructions.md` thin (repo overview + pointers) and **inline each workflow
  skill's essence into the prompt files that need it** (`wf-spec`/`wf-plan`/`wf-tasks` each
  carry the spec-driven conventions they enforce).

## Deliverables

```
adapters/copilot/
├── generate.py            # reads plugin → emits .github/{prompts,chatmodes,instructions},
│                          #   .vscode/mcp.json, lefthook.yml
├── README.md              # honest support-tier table (mirror adapters/opencode/README.md)
└── githooks/lefthook.yml  # static enforcement asset (analog of opencode's plugin/wellforge.js)
config/model-tiers.yml     # + copilot: block (tiers → Copilot model names per subscription)
docs/PLAN.md               # + adapters/Copilot line
```

`generate.py` swaps only the emit functions vs. the OpenCode generator; `translate` gains a
Copilot variant (`/wellforge:x`→`/wf-x`, `$ARGUMENTS`→`${input:args}`, bare agent refs→
`wf-<agent>`).

## Build order

1. ☑ **Scaffold generator** off `adapters/opencode/generate.py`; add `copilot:` to
   `model-tiers.yml`.
2. ☑ **Emit prompts** (`gen_prompts`) — 17 commands → `.github/prompts/wf-*.prompt.md`;
   `$ARGUMENTS` → `${input:args}` seeded with `argument-hint`.
3. ☑ **Emit chat modes** (`gen_chatmodes`) — 10 agents → `.github/chatmodes/wf-*.chatmode.md`
   with routed `model` + tool allowlist; designer's Edit-only denial noted (not representable).
4. ☑ **Emit instructions** — 9 glob-scoped `.instructions.md` pointers + full skill library in
   `.github/wf-skills/` + thin `.github/copilot-instructions.md`.
5. ☑ **Emit `.vscode/mcp.json`** from `.mcp.json` (3 servers, non-clobbering merge).
6. ☑ **Enforcement fallback** — static `lefthook.yml` (secret-scan, lint, spec-drift,
   compile); non-destructive if one already exists.
7. ☑ **README + PLAN** — `adapters/copilot/README.md` with the honest support-tier table and
   the two declared gaps.
8. ☐ **Validate** — end-to-end generator run green (frontmatter YAML valid, 0 leftover
   `/wellforge:` refs); **remaining:** manual VS Code smoke test that prompts / chat modes /
   MCP load in a real session.

## Recommendation

Ship as a **generator adapter mirroring OpenCode** for the first cut (same status OpenCode is
at today), not a copier-emitted layer. Later, wire tool choice into `wellforge setup/migrate`
(already the noted next step for OpenCode) so a project can lay down either adapter
automatically. First milestone = **prompts + chat modes + instructions + MCP** — the workflow,
agents, and skills, i.e. the bulk of WellForge; enforcement fallback and the orchestration
honesty note follow.
</content>
</invoke>
