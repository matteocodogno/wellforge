# WellForge Claude Code Plugin

Full-stack development plugin for Spring Boot Kotlin + React TypeScript monorepos.

## Install

There are two ways to use a local plugin. Pick one:

### Option A — one-shot (no setup, use for testing)

Pass the plugin directory every time you launch:

```bash
claude --plugin-dir <wellforge-checkout>/wellforge-plugin
```

### Option B — permanent via local marketplace (recommended)

The **wellforge repo root** is a plugin marketplace (`.claude-plugin/marketplace.json`
with a relative plugin source — nothing to edit). Set up once, works across all projects:

```bash
# 1. Register the marketplace (repo root, not this directory)
claude plugin marketplace add <wellforge-checkout>

# 2. Install
claude plugin install wellforge@wellforge --scope user
```

(or interactively: `/plugin` → wellforge → install → scope: user)

### Verify

Inside Claude Code:
```
/plugin   → wellforge listed under Installed
/mcp      → sequential-thinking, playwright, github connected
/hooks    → 7 hooks listed
```

---

## Structure

| Path | What |
|---|---|
| `.mcp.json` | sequential-thinking, playwright, github MCP servers |
| `commands/spec.md` | `/wellforge:spec` — interview → feature spec (step 1 of 3) |
| `commands/plan.md` | `/wellforge:plan` — approved spec → technical plan (step 2 of 3) |
| `commands/tasks.md` | `/wellforge:tasks` — approved plan → dependency-aware task list (step 3 of 3) |
| `commands/implement.md` | `/wellforge:implement` — implement chosen tasks (IDs/range/next/all), parallel by DAG, QE-verified |
| `commands/status.md` | `/wellforge:status` — recap every feature's phase + the next command to run (read-only) |
| `commands/orchestrate.md` | `/wellforge:orchestrate` — full team pipeline: classify → spec → plan → tasks → parallel devs → QE verdict, 2 human gates |
| `commands/new.md` | `/wellforge:new` — interview → stack recommendation → Copier scaffold → build verify → connections |
| `commands/upgrade.md` | `/wellforge:upgrade` — copier update to a newer template version + AI conflict resolution + gates |
| `commands/adopt.md` | `/wellforge:adopt` — brownfield onboarding: AI-readiness, spec workflow, gates with measured baseline |
| `commands/eval.md` | `/wellforge:eval` — LM-judge scores the feature against the central rubric (gate into `done`) |
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
| `hooks/scripts/pre-bash-guard.sh` | Blocks rm -rf /, SQL nukes, pipe-to-shell, .env writes |
| `hooks/scripts/post-lint.sh` | ts/tsx → Prettier+ESLint · kt/kts → ktlintFormat |
| `hooks/scripts/notify.sh` | macOS notification + Telegram DM |
| `hooks/scripts/stop-verify.sh` | Checks spec drift + tsc before Claude stops |
| `hooks/scripts/pre-compact-backup.sh` | Snapshots session state before compaction |
| `hooks/scripts/trace-subagent.sh` | SubagentStop → best-effort token events to `.forge/runs/.events.jsonl` (observability) |
| `scripts/run-report.py` | Summarizes `.forge/runs/` — agents, verdicts, drift, estimated cost |
| `scripts/check-routing.py` | Verifies agent frontmatter models match the routing policy (drift guard) |
| `config/model-pricing.yml` | Per-model price table for run-report cost estimates |
| `config/model-routing.yml` | Model-routing policy: agent → tier (frontier/mid/cheap) — drives OpEx down |
| `skills/spec-driven/` | Spec-driven workflow conventions (format, status lifecycle, drift rule) |
| `skills/observability/` | Run-trace (`.forge/runs/`) format conventions — producers and consumers |
| `skills/connections/` | Standardized tool-connection checklists (GitHub, MCP, environments) — each ends with a verification command |
| `skills/react-ts-vite/` | React + TypeScript + Vite + Mantine + TanStack |
| `skills/kotlin-springboot/` | Spring Boot + Kotlin + jOOQ + Liquibase + Modulith |
| `skills/springboot-scaffold/` | Scaffolds a new full-stack service |

## MCP servers

| Server | Transport | Auth |
|---|---|---|
| `sequential-thinking` | stdio | none |
| `playwright` | stdio | none |
| `github` | HTTP | OAuth via `/mcp` on first use |

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
