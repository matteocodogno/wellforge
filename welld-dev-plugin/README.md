# welld-dev Claude Code Plugin

Full-stack development plugin for welld Spring Boot Kotlin + React TypeScript monorepos.

## Install

There are two ways to use a local plugin. Pick one:

### Option A — one-shot (no setup, use for testing)

Pass the plugin directory every time you launch:

```bash
claude --plugin-dir <wellforge-checkout>/welld-dev-plugin
```

### Option B — permanent via local marketplace (recommended)

The **wellforge repo root** is a plugin marketplace (`.claude-plugin/marketplace.json`
with a relative plugin source — nothing to edit). Set up once, works across all projects:

```bash
# 1. Register the marketplace (repo root, not this directory)
claude plugin marketplace add <wellforge-checkout>

# 2. Install
claude plugin install welld-dev@welld --scope user
```

(or interactively: `/plugin` → welld-dev → install → scope: user)

### Verify

Inside Claude Code:
```
/plugin   → welld-dev listed under Installed
/mcp      → sequential-thinking, playwright, github connected
/hooks    → 6 hooks listed
```

---

## Structure

| Path | What |
|---|---|
| `.mcp.json` | sequential-thinking, playwright, github MCP servers |
| `commands/spec.md` | `/welld-dev:spec` — interview → feature spec (step 1 of 3) |
| `commands/plan.md` | `/welld-dev:plan` — approved spec → technical plan (step 2 of 3) |
| `commands/tasks.md` | `/welld-dev:tasks` — approved plan → dependency-aware task list (step 3 of 3) |
| `commands/orchestrate.md` | `/welld-dev:orchestrate` — full team pipeline: classify → spec → plan → tasks → parallel devs → QE verdict, 2 human gates |
| `commands/new.md` | `/welld-dev:new` — interview → stack recommendation → Copier scaffold → build verify → connections |
| `commands/upgrade.md` | `/welld-dev:upgrade` — copier update to a newer template version + AI conflict resolution + gates |
| `commands/adopt.md` | `/welld-dev:adopt` — brownfield onboarding: AI-readiness, spec workflow, gates with measured baseline |
| `agents/product-owner.md` | PO — spec.md: problem, user stories, ACs, non-goals |
| `agents/architect.md` | Architect — plan.md: architecture, contracts, AC→test mapping |
| `agents/designer.md` | Designer — design.md: flows, screens, component reuse, a11y |
| `agents/frontend-dev.md` | FE dev — implements tasks per react-ts-vite conventions |
| `agents/backend-dev.md` | BE dev — implements tasks per stack skill conventions |
| `agents/devops.md` | DevOps — CI/CD, infra, tool connections (verified, not assumed) |
| `agents/quality-engineer.md` | QE — AC verification, gates run, evidence-based verdict |
| `agents/owasp-reviewer.md` | Specialist: OWASP Top 10 security review |
| `agents/adr-writer.md` | Specialist: Architecture Decision Record writer |
| `hooks/hooks.json` | 6 lifecycle hooks |
| `hooks/scripts/session-start.sh` | Injects git state + domain glossary at session start |
| `hooks/scripts/pre-bash-guard.sh` | Blocks rm -rf /, SQL nukes, pipe-to-shell, .env writes |
| `hooks/scripts/post-lint.sh` | ts/tsx → Prettier+ESLint · kt/kts → ktlintFormat |
| `hooks/scripts/notify.sh` | macOS notification + Telegram DM |
| `hooks/scripts/stop-verify.sh` | Checks spec drift + tsc before Claude stops |
| `hooks/scripts/pre-compact-backup.sh` | Snapshots session state before compaction |
| `skills/spec-driven/` | Spec-driven workflow conventions (format, status lifecycle, drift rule) |
| `skills/connections/` | Standardized tool-connection checklists (GitHub, MCP, environments) — each ends with a verification command |
| `skills/react-ts-vite/` | React + TypeScript + Vite + Mantine + TanStack |
| `skills/kotlin-springboot-welld/` | Spring Boot + Kotlin + jOOQ + Liquibase + Modulith |
| `skills/springboot-scaffold/` | Scaffolds a new welld-style service |

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
- **bolla**: work order issued to external contractors
- **ditta esterna**: external maintenance company
```
