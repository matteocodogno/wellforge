---
name: connections
description: >
  Standardized checklists for connecting a WellForge project to its ecosystem tools — GitHub
  (repo, branch protection, secrets), CI, MCP servers, environments and databases. Use
  during /wellforge:new stage 5, when the user asks to "connect", "set up", or "wire up"
  a tool/integration for a project, or when the devops agent needs the standard procedure.
  Every checklist ends with a verification command: a connection is established only when
  that command's output says so.
---

# Connections — standardized ecosystem setup

One way to connect each tool, the same for every project. The core rule: **"connected"
is an observed fact** — each checklist ends with a verification command; run it and read
the output. Never report a connection done without it.

References (read the one you need):
- `references/github.md` — repo creation, branch protection, CI secrets
- `references/mcp-servers.md` — the standard MCP set for WellForge projects
- `references/environments.md` — env vars, secrets hygiene, local DB

## Order

When connecting a fresh project, follow this order (later steps depend on earlier ones):

1. **GitHub repo + push** — everything else hangs off the remote.
2. **Branch protection** — before anyone (human or agent) pushes to main.
3. **CI secrets/variables** — before the first PR triggers the gate workflows.
4. **MCP servers** — project `.mcp.json` (usually scaffolded; verify, don't recreate).
5. **Environments / DB** — local docker-compose up + connection check.

## Conduct

- Idempotency: every checklist starts with its verification command — if it already
  passes, report "already connected" and move on. Never re-create existing resources.
- Anything requiring org-admin rights or interactive OAuth you cannot complete: do the
  steps you can, then output the exact command/URL for the human, and mark the item
  PENDING — never silently skip it.
- Secrets: values come from the user or a secret manager at setup time; they never land
  in the repo, the chat transcript (mask them), or shell history when avoidable
  (`gh secret set X < file` / `--body` from env, not inline literals).
- Record the outcome: append a "Connections" status table (tool / status / verified-by)
  to the project README — connected, pending, or skipped-by-choice.
