# groma.md — the live architecture map

[groma.md](https://github.com/MrLesk/Groma.md) scans the repository into a C4 map stored as
OKF Markdown in `groma/`, committed and reviewed in the same PR as the code. A deterministic
scan (no AI service, no account, offline once scanners are installed) gives the first map;
people or agents curate it and later scans keep the curation.

**Default: offered, and a yes unless the user declines.** It is opt-out, not mandatory — a
declined or skipped item is recorded in the README "Connections" table as
`skipped-by-choice`. Not offered at the `spike` tier.

## What it is for here

| WellForge piece | Use |
|---|---|
| `architect` | reads `groma view --plain` as the as-built architecture before planning; the plan's `## Architecture` names the component ids it touches |
| `/wellforge:improve-architecture` | the map and `groma lint` are evidence next to git co-change |
| ADRs | **unchanged** — decisions stay in `docs/adr/`; the map records what exists, an ADR records why |

Groma owns `groma/`. **Never edit those files by hand**, in any tier — go through the
`groma` CLI (`groma agent-instructions` is the index). It is not a task system: WellForge's
tasks live in `specs/NNN-slug/tasks.md`, see "Backlog.md" below.

## Pin

`groma.md@0.6.6` (pre-1.0 — pin it, treat a bump as a deliberate change). macOS needs Apple
Silicon. Run it through `npx -y groma.md@0.6.6 …`, or `mise use npm:groma.md@0.6.6` to put it
in the project's `mise.toml` `[tools]`. Do not `npm i -g` it in a setup — that is machine
state nothing records.

## Checklist

1. **Already connected?** `test -f groma/project.md && npx -y groma.md@0.6.6 scan` — if it
   exits 0, report "already connected" and stop.
2. **Backlog.md guard.** `command -v backlog`. `groma init` bootstraps Backlog.md when that
   CLI is on PATH: it creates `backlog/` and writes a long block into `AGENTS.md` telling
   every agent to run `backlog instructions overview` first — a second, competing task
   system. Run step 3 with its directory off PATH, for that one command only:
   `BDIR=$(dirname "$(command -v backlog)"); env PATH="$(echo "$PATH" | tr ':' '\n' | grep -vxF "$BDIR" | paste -sd: -)" npx -y groma.md@0.6.6 init …`
   (if `node` lives in that same directory, put it back — a PATH with no node fails with a
   mise shim error that looks like a groma bug).
   If the user *wants* Backlog.md,
   that is their call — say it overlaps `tasks.md` and let them decide.
3. **Init.** `npx -y groma.md@0.6.6 init --directory groma <project-name>` — `--directory`
   is required. Writes `groma/` and a short marked block (`<!-- groma:start -->`) into
   `AGENTS.md` and `CLAUDE.md`. Leave the block; it is how a later agent finds the guide.
4. **Scanners.** `npx -y groma.md@0.6.6 scanner discover` lists what applies to this repo.
   Install the `installable` ones with `scanner add <source>`. Starting points by preset:
   `hono-react` / `pulumi-gcp-ts` → `@groma/scanner-typescript`;
   `spring-kotlin-react` → the Java and TypeScript scanners (Kotlin is *experimental* — say
   so in the README rather than presenting a thin map as complete). Trust `discover` over
   this list; Python is `@groma/scanner-python`. **Set `exclude` in `groma/scanners.json`
   before the first scan** (tests, fixtures, generated code, templates): excluding afterwards
   keeps the components already stored, and removing one means deleting its source.
5. **First scan.** `npx -y groma.md@0.6.6 scan`. Expect "First scan. Ask your coding agent
   to curate this architecture." — the map is a starting point, **not** a verified
   architecture. Say that to the user.
6. **Curate (on a yes).** Containers must come from the scan to be real — a hand-drafted
   container stays a dashed *draft* until a scan matches code to it, so `combine` the
   scanner's containers (`edit <keep> --combine <absorbed…>`, then `--id`) instead of
   drafting; draft only for what no scanner reads (Markdown, templates). Main loop, `groma agent-instructions` then the guide it names
   (`inspect` → `structure` → `describe` → `relationships`). Use the CLI only. Report what
   changed and what stayed uncertain.
7. **Commit** `groma/` with the code, as `chore: add groma.md architecture map`.

## Verify

```bash
test -f groma/project.md && npx -y groma.md@0.6.6 view --plain >/dev/null && echo "connected"
```

`connected` printed = established. Report separately whether the map is still a first scan
(uncurated) — connected and curated are different facts.

## CI (optional, PENDING until a human adds it)

A PR architecture diff exists as a separate action
(`MrLesk/groma.md-action`). It runs on `origin`, needs a workflow added by someone with repo
rights, and is third-party — pin it to a commit SHA, read it first, and list it PENDING
rather than adding it silently. Never wire it as a required status check without asking.

## Common failures

| Symptom | Fix |
|---|---|
| `--directory is required when Groma is not initialized` | pass `--directory groma` |
| `backlog/` appeared, AGENTS.md has a Backlog block | step 2 was skipped — delete `backlog/` and that marked block, re-run with it off PATH |
| `mise ERROR No version is set for shim: groma` | a stale mise shim — use `npx -y groma.md@0.6.6` or `mise use npm:groma.md@0.6.6` |
| map is dozens of `helper`/`config` boxes | scanner picked up templates/fixtures — add them to `exclude` in `groma/scanners.json` |
| scan says unresolved dynamic dispatch / framework wiring | expected — scanners read source syntax; curate relationships by hand |
