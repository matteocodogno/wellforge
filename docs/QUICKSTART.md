# WellForge — Quick start (greenfield project)

From product idea to a building, CI-gated, spec-driven repo — target: **under 30 minutes**.
Assumes [installation](INSTALLATION.md) is done.

## 1. Scaffold

Open Claude Code in the directory where the project should live and run:

```
/welld-dev:new a portal where external contractors manage their work orders
```

What happens (you stay in the loop at every decision):

1. **Interview** — a couple of question rounds: who uses it, expected lifetime/scale,
   domain complexity, anything already decided (DB, auth, hosting).
2. **Stack recommendation** — one of the two presets, with the rationale and why not the
   other. You confirm or override; your choice wins.

   | Preset | Pick when |
   |---|---|
   | `spring-kotlin-react` | rich domain logic, transactions, long-lived product |
   | `hono-react` | lightweight API, fast iteration, all-TS team |

3. **Generation** — Copier renders the project; first commit is the pristine scaffold.
4. **Build verification** — `mise run install`, `build`, `test` must pass before
   anything else happens.
5. **Connections** — guided checklists: GitHub repo + branch protection, CI variables,
   MCP servers, local DB. Each ends with a verification command you can see pass.
   Steps needing org rights you don't have become explicit PENDING items.

You now have a repo with: pinned toolchain (`mise.toml`), CI calling the central quality
gates, project `CLAUDE.md` (AI-ready on first open), `specs/` directory, and
`.forge/manifest.json` recording template+version for future upgrades.

### Manual generation (no AI session)

```bash
uvx copier copy --trust <wellforge repo/URL> my-project --data preset=hono-react
cd my-project && git init -b main && git add -A && git commit -m "chore: scaffold"
mise trust && mise install && mise run install && mise run build && mise run test
```

## 2. First feature — spec-driven

Two ways to work. Either drive the steps yourself:

```
/welld-dev:spec contractors can accept or reject an assigned work order
# review → approve
/welld-dev:plan
# review architecture + AC→test mapping → approve
/welld-dev:tasks
# review task list, then implement tasks of the feature — dependency-aware, QE-verified.
# arg is [feature] [tasks]; the feature folder (specs/NNN-slug) leads, tasks follow:
/welld-dev:implement 001-user-auth next     # first ready task of that feature
/welld-dev:implement 001-user-auth T3,T5    # a chosen subset
/welld-dev:implement all                    # all ready tasks (feature inferred if only one in-progress)
```

…or let the orchestrator run the whole pipeline (you still approve spec and plan —
exactly two pauses):

```
/welld-dev:orchestrate contractors can accept or reject an assigned work order
```

The orchestrator routes work to the agent team (PO → Architect → Designer if UI → devs
in parallel → QE verdict) and ends with an evidence-based gate report.

Rules worth knowing on day one:

- Only **you** approve specs and plans — nothing self-approves.
- If code and spec disagree, the spec gets amended first (a Stop hook blocks sessions
  that change a spec without re-syncing tasks).
- Commits reference tasks: `feat(orders): accept endpoint (T3, specs/001)`.

## 3. Day-2 routine

| Need | Do |
|---|---|
| daily dev | `mise run dev` · `mise run test` · `mise run lint` |
| new feature | `/welld-dev:spec` → `:plan` → `:tasks` → `:implement` (or `:orchestrate` for all of it) |
| implement a feature's tasks | `/welld-dev:implement <feature> T3,T5` · `<feature> next` · `all` |
| where am I / what's next | `/welld-dev:status` (all features + next command each) |
| bugfix | `/welld-dev:orchestrate <bug>` → QE writes the failing repro test first |
| CI red on the quality gate | the gate report names the exact threshold; thresholds are central — fix the code, don't look for a config to weaken (there isn't one in your repo) |
| template released a new version | `/welld-dev:upgrade` — diff explained, conflicts resolved with you, gates re-run, one revertable commit |
| check the fleet | `scripts/fleet-status.sh <github-org>` (from the wellforge repo) |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `mise: command not found` tasks in CI/local | `mise trust` in the project root, shell activation in your rc file |
| gate fails: `pnpm-lock.yaml missing` | `mise run install` locally, commit the lockfile (reproducibility gate — intended) |
| `/welld-dev:*` commands missing | plugin not installed in this scope — see [Installation §3–4](INSTALLATION.md) |
| upgrade refuses to run | working tree must be clean — commit or stash first (by design) |
| postgres tests fail locally | Docker running? `docker compose up -d db`, then `docker compose exec db pg_isready` |

---

Deeper dives: [Features](FEATURES.md) · [Template contract](../templates/_shared/CONTRACT.md) · [Gates policy](../gates/README.md)
