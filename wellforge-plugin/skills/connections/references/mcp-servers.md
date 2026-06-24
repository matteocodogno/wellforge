# MCP servers — standard WellForge set

Scaffolded projects ship a `.mcp.json`; the wellforge plugin also provides servers
plugin-wide. **Verify before creating** — duplicate server names shadow each other.

## Standard set

| Server | Why | Transport |
|---|---|---|
| `sequential-thinking` | complex planning support | stdio (npx) |
| `playwright` | designer/QE browser automation | stdio (npx) |
| `github` | PRs, issues, CI runs from the session | HTTP + OAuth |

Provided by the wellforge plugin's `.mcp.json` — projects do NOT need to re-declare
them. A project-local `.mcp.json` is only for project-specific servers (e.g. a
database MCP pointed at the project's local DB, an internal API's MCP).

## Adding a project-specific server

```jsonc
// .mcp.json (project root, committed — no secrets in here)
{
  "mcpServers": {
    "postgres-local": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres",
               "postgresql://localhost:5432/${POSTGRES_DB}"]
    }
  }
}
```

Secrets/connection strings come from env (`${VAR}` expansion), never literals.

## Verify

Inside a Claude Code session in the project:
```
/mcp        → every expected server listed as connected
```
From the shell (server boots at all):
```bash
npx -y @modelcontextprotocol/server-postgres --help >/dev/null && echo "launchable"
```
For OAuth servers (github): first use triggers the flow — confirm with a real call
(e.g. ask the session to list open PRs). PENDING until a human completes OAuth.

## Common failures

| Symptom | Fix |
|---|---|
| server listed but "failed" | run the command manually — usually a missing env var |
| works for you, not for teammate | env var documented? add to README "Pending setup" |
| two servers same name | project `.mcp.json` shadows plugin — rename the project one |
