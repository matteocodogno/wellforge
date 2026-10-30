# Environments — env vars, secrets hygiene, local DB

## Env var layering (WellForge standard, via mise)

| Layer | File | Committed | Contents |
|---|---|---|---|
| defaults | `mise.toml` `[env]` | yes | non-sensitive defaults (ports, feature flags) |
| machine-local | `.mise.local.toml` | **never** (gitignored by scaffold) | secrets, local overrides |
| CI | GitHub secrets/variables | n/a | see `references/github.md` |

Rule: a fresh clone + `mise trust && mise install` + documented `.mise.local.toml` keys
must be enough to run the project. Every required local key is listed in the project
README — names only, never values.

**There is no dotenv layer.** That is not an omission from the table — it is the table. The
app presets used to ship a committed `frontend/.env` holding the public `VITE_*` defaults,
which contradicted row one and could not be maintained by an agent anyway, since the
plugin's guards refuse to read or write a file named `.env`. Those defaults are now row one:
the root `mise.toml` `[env]` block. Vite reads `VITE_`-prefixed vars from the process
environment and prefers them over a dotenv file, so `mise run frontend:dev` / `:build` pick
them up with no `envDir`/`envPrefix` configuration.

Adding a browser-exposed var therefore touches two committed files and no third one:
`frontend/src/vite-env.d.ts` for the type, root `mise.toml` for the value. Anything
`VITE_`-prefixed is inlined into the bundle and is public by construction — a secret in that
block is a secret on your website.

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

The plugin's guards block commands that read or write a secret file — work with them: put
secrets in `.mise.local.toml`, not a dotenv file. The `git check-ignore` line above is
deliberately a **metadata** query, which the guards allow precisely because it reveals
nothing of the contents; a read of the same paths is refused, including
`.mise.local.toml` itself (write it, don't read it back — `mise env` shows the resolved
values).

## Common failures

| Symptom | Fix |
|---|---|
| app can't see var that `mise env` shows | process not started via mise — use `mise run dev` / `mise exec` |
| Testcontainers fails locally | Docker not running, or arch mismatch — `docker info` first |
| works locally, CI red | var exists in `.mise.local.toml` but not as CI variable — sync names |
