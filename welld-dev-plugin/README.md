# welld-dev Claude Code Plugin

Full-stack development plugin for welld Spring Boot Kotlin + React TypeScript monorepos.

## Install

There are two ways to use a local plugin. Pick one:

### Option A — one-shot (no setup, use for testing)

Pass the plugin directory every time you launch:

```bash
claude --plugin-dir ~/.ai/plugins/welld-dev-plugin
```

### Option B — permanent via local marketplace (recommended)

Set up once, works across all projects:

```bash
# 1. Edit marketplace.json: replace __PLUGIN_DIR__ with the absolute path to this folder
#    Example: /Users/matteocodogno/.ai/plugins/welld-dev-plugin
sed -i '' 's|__PLUGIN_DIR__|'"$HOME/.ai/plugins/welld-dev-plugin"'|' marketplace.json

# 2. Register the local marketplace with Claude Code
claude plugin marketplace add ~/.ai/plugins/welld-dev-plugin/marketplace.json --scope user

# 3. Inside Claude Code, install from the marketplace
/plugin    # → find welld-dev → install → scope: user
```

Or install via CLI after registering the marketplace:

```bash
claude plugin install welld-dev@welld --scope user
```

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

Add to `~/.zshrc` — **never commit**:
```bash
export TELEGRAM_BOT_TOKEN="your-token-here"
export TELEGRAM_CHAT_ID="your-chat-id-here"
```

Get your chat ID (send any message to your bot first):
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates"
# → find "chat":{"id": 123456789}
```

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
