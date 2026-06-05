# Environments — env vars, secrets hygiene, local DB

## Env var layering (welld standard, via mise)

| Layer | File | Committed | Contents |
|---|---|---|---|
| defaults | `mise.toml` `[env]` | yes | non-sensitive defaults (ports, feature flags) |
| machine-local | `.mise.local.toml` | **never** (gitignored by scaffold) | secrets, local overrides |
| CI | GitHub secrets/variables | n/a | see `references/github.md` |

Rule: a fresh clone + `mise trust && mise install` + documented `.mise.local.toml` keys
must be enough to run the project. Every required local key is listed in the project
README — names only, never values.

**Verify:** `mise env | grep -E '<EXPECTED_VAR>'` shows the var resolved (value masked
in your report).

## Local database (postgres presets)

The scaffold ships `docker-compose.yml`; Spring Boot's docker-compose support starts it
automatically. Manual path:

```bash
docker compose up -d db
```

**Verify:**
```bash
docker compose ps --format '{{.Name}} {{.Status}}'   # db ... Up (healthy)
docker compose exec db pg_isready -U "$POSTGRES_USER" # accepting connections
```
Backend-level check (JVM stack): `mise run backend:test` — Testcontainers/integration
tests hitting the DB are the real verification.

## Secrets hygiene checks

Before finishing any environment setup:

```bash
# Nothing sensitive staged
git diff --cached --name-only | grep -E '\.(env|local\.toml)$' && echo "STOP: secret file staged"
# Local files properly ignored
git check-ignore .mise.local.toml .env.local 2>/dev/null
```

The plugin's `pre-bash-guard.sh` blocks `.env` writes in sessions — work with it: put
secrets in `.mise.local.toml`, not `.env`.

## Common failures

| Symptom | Fix |
|---|---|
| app can't see var that `mise env` shows | process not started via mise — use `mise run dev` / `mise exec` |
| Testcontainers fails locally | Docker not running, or arch mismatch — `docker info` first |
| works locally, CI red | var exists in `.mise.local.toml` but not as CI variable — sync names |
